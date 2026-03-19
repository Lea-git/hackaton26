<?php

use Illuminate\Support\Facades\Route;
use Illuminate\Support\Facades\Auth;
use Illuminate\Http\Request;
use App\Models\Document;
use App\Models\Fournisseur;
use Illuminate\Support\Facades\Storage;  
use App\Services\DataLakeClient;
use Illuminate\Support\Facades\Log;

// Route de secours pour le middleware auth
Route::get('/login', function () {
    return redirect('/user/login');
})->name('login');

// Page d'accueil
Route::get('/', function () {
    return view('welcome');
});

// Route d'upload MULTI-DOCUMENTS (MODIFIÉE)
Route::post('/upload', function (Request $request) {
    // Validation des fichiers multiples
    $request->validate([
        'documents' => 'required|array|min:1|max:10',
        'documents.*' => 'required|file|mimes:pdf,jpg,jpeg,png|max:10240'
    ], [
        'documents.required' => 'Sélectionnez au moins un fichier',
        'documents.max' => 'Maximum 10 fichiers à la fois',
        'documents.*.mimes' => 'Format accepté : PDF, JPG, PNG',
        'documents.*.max' => 'Chaque fichier doit faire moins de 10 Mo'
    ]);

    $uploadedFiles = $request->file('documents');
    $successCount = 0;
    $errors = [];

    foreach ($uploadedFiles as $fichier) {
        try {
            // 1. Stockage local
            $chemin = $fichier->store('documents', 'public');
            
            // 2. Sauvegarde en BDD
            $document = Document::create([
                'nom_fichier_original' => $fichier->getClientOriginalName(),
                'chemin_stockage' => $chemin,
                'type_document' => 'non_classe',
                'statut_ocr' => 'en_attente',
                'mime_type' => $fichier->getMimeType(),
                'taille_fichier' => $fichier->getSize()
            ]);
            
            // 3. Envoi vers le Data Lake (RAW zone) pour OCR
            try {
                $dataLakeClient = new DataLakeClient();
                $uploaded = $dataLakeClient->uploadRaw($fichier, $fichier->getClientOriginalName());
                
                if ($uploaded) {
                    Log::info('Document envoyé au Data Lake: ' . $fichier->getClientOriginalName());
                }
            } catch (\Exception $e) {
                Log::error('Erreur envoi Data Lake: ' . $e->getMessage());
                // On continue même si l'envoi au Data Lake échoue
            }
            
            $successCount++;
            
        } catch (\Exception $e) {
            $errors[] = $fichier->getClientOriginalName() . ': ' . $e->getMessage();
        }
    }

    // Message de retour personnalisé
    if ($successCount > 0) {
        $message = $successCount . ' fichier(s) uploadé(s) avec succès';
        if (!empty($errors)) {
            $message .= ' (' . count($errors) . ' échec(s))';
        }
        return redirect('/user/dashboard')->with('success', $message);
    } else {
        return redirect('/user/dashboard')->with('error', 'Aucun fichier n\'a pu être uploadé');
    }
    
})->name('upload');

// Routes user
Route::prefix('user')->group(function () {
    Route::get('/login', function () {
        return view('user.login', ['espace' => 'Utilisateur']);
    })->name('user.login');
    
    Route::post('/login', function (Illuminate\Http\Request $request) {
        $credentials = $request->validate([
            'email' => 'required|email',
            'password' => 'required'
        ]);

        if (Auth::attempt($credentials)) {
            $request->session()->regenerate();
            
            $user = Auth::user();
            
            if ($user->role === 'commercial') {
                return redirect('/user/dashboard');
            }
            return redirect('/');
        }

        return back()->withErrors([
            'email' => 'Identifiants incorrects.',
        ]);
    });
    
    // DASHBOARD USER
    Route::get('/dashboard', function () {
        // 1. Documents locaux
        $documentsLocaux = Document::latest()->take(10)->get();
        
        // 2. Documents du Data Lake
        $dataLakeClient = new DataLakeClient();
        try {
            $documentsCurated = $dataLakeClient->getCuratedDocuments();
            if (empty($documentsCurated)) {
                $documentsCurated = $dataLakeClient->getMockDocuments();
            }
        } catch (\Exception $e) {
            $documentsCurated = $dataLakeClient->getMockDocuments();
        }
        
        // 3. Données de l'étudiant 2 (OCR) avec mise à jour des fournisseurs
        $documentsOCR = [];
        try {
            $jsonContent = Storage::disk('public')->get('ocr_data.json');
            $rawData = json_decode($jsonContent, true) ?? [];
            
            // Normaliser en tableau
            if (isset($rawData[0])) {
                $documentsOCR = $rawData;
            } else {
                $documentsOCR = [$rawData];
            }
            
            // Mise à jour automatique des fournisseurs
            foreach ($documentsOCR as $ocrData) {
                $nomEntreprise = $ocrData['fields']['nom_entreprise'] ?? 
                                 $ocrData['vendor_name'] ?? 
                                 null;
                
                $siret = $ocrData['fields']['siret'] ?? 
                        $ocrData['siret'] ?? 
                        null;
                
                $siren = $siret ? substr($siret, 0, 9) : null;
                
                if ($nomEntreprise) {
                    Fournisseur::firstOrCreate(
                        ['nom' => $nomEntreprise],
                        [
                            'siren' => $siren,
                            'siret' => $siret,
                            'statut' => 'actif'
                        ]
                    );
                }
            }
            
        } catch (\Exception $e) {
            Log::warning('Erreur chargement OCR: ' . $e->getMessage());
            $documentsOCR = [];
        }
        
        // 4. Récupérer tous les fournisseurs
        $fournisseurs = Fournisseur::withCount('documents')->get();
        
        // 5. STATISTIQUES DYNAMIQUES
        $totalDocuments = Document::count();
        $documentsMois = Document::whereMonth('created_at', now()->month)
            ->whereYear('created_at', now()->year)
            ->count();
        $enAttente = Document::where('statut_ocr', 'en_attente')->count();
        $traites = Document::where('statut_ocr', 'traite')->count();
        
        return view('user.dashboard', [
            'documentsLocaux' => $documentsLocaux,
            'documentsCurated' => $documentsCurated,
            'documentsOCR' => $documentsOCR,
            'fournisseurs' => $fournisseurs,
            'totalDocuments' => $totalDocuments,
            'documentsMois' => $documentsMois,
            'enAttente' => $enAttente,
            'traites' => $traites
        ]);
    })->name('user.dashboard');
});

// Routes admin
Route::prefix('admin')->group(function () {
    Route::get('/login', function () {
        return view('admin.login', ['espace' => 'Administrateur']);
    })->name('admin.login');
    
    Route::post('/login', function (Illuminate\Http\Request $request) {
        $credentials = $request->validate([
            'email' => 'required|email',
            'password' => 'required'
        ]);

        if (Auth::attempt($credentials)) {
            $request->session()->regenerate();
            
            $user = Auth::user();
            
            if ($user->role === 'conformite') {
                return redirect('/admin/dashboard');
            }
            return redirect('/');
        }

        return back()->withErrors([
            'email' => 'Identifiants incorrects.',
        ]);
    });
    
    // DASHBOARD ADMIN
    Route::get('/dashboard', function () {
        // Récupère les documents depuis le Data Lake (curated zone)
        $dataLakeClient = new DataLakeClient();
        try {
            $documentsCurated = $dataLakeClient->getCuratedDocuments();
            if (empty($documentsCurated)) {
                $documentsCurated = $dataLakeClient->getMockDocuments();
            }
        } catch (\Exception $e) {
            $documentsCurated = $dataLakeClient->getMockDocuments();
        }
        
        // Transforme les données de l'étudiant 5 au format attendu par le dashboard
        $documentsAdaptes = [];
        foreach ($documentsCurated as $doc) {
            $documentsAdaptes[] = [
                'document_id' => $doc['document_id'] ?? ($doc['metadata']['document_type'] ?? 'N/A'),
                'document_type' => $doc['document_type'] ?? ($doc['metadata']['document_type'] ?? 'N/A'),
                'fournisseur' => $doc['fournisseur'] ?? ($doc['metadata']['api_company_name'] ?? $doc['metadata']['input_vendor_name'] ?? 'Inconnu'),
                'siret' => $doc['siret'] ?? 'N/A',
                'montant_ttc' => $doc['montant_ttc'] ?? 0,
                'coherence_ok' => ($doc['status'] ?? 'INVALID') === 'VALID',
                'anomalies' => $doc['anomalies'] ?? ($doc['metadata']['errors'] ?? [])
            ];
        }
        
        // Calcule les stats
        $totalDocs = count($documentsAdaptes);
        $conformes = 0;
        $alertesRouges = 0;
        $alertesOranges = 0;
        
        foreach ($documentsAdaptes as $doc) {
            if ($doc['coherence_ok']) {
                $conformes++;
            } else {
                $nbAnomalies = count($doc['anomalies'] ?? []);
                if ($nbAnomalies > 1) {
                    $alertesRouges++;
                } else {
                    $alertesOranges++;
                }
            }
        }
        
        return view('admin.dashboard', [
            'documentsCurated' => $documentsAdaptes,
            'totalDocs' => $totalDocs,
            'conformes' => $conformes,
            'alertesRouges' => $alertesRouges,
            'alertesOranges' => $alertesOranges
        ]);
    })->name('admin.dashboard');
});

// Logout
Route::post('/logout', function (Illuminate\Http\Request $request) {
    Auth::logout();
    $request->session()->invalidate();
    $request->session()->regenerateToken();
    return redirect('/');
})->name('logout');