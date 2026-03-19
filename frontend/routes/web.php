<?php

use Illuminate\Support\Facades\Route;
use Illuminate\Support\Facades\Auth;
use Illuminate\Http\Request;
use App\Models\Document;
use App\Models\Extraction;
use App\Models\Alerte;
use Illuminate\Support\Facades\Storage;
use App\Services\DataLakeClient;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Http;

// Page d'accueil
Route::get('/', function () {
    return view('welcome');
});

// Route d'upload multi-documents
Route::post('/upload', function (Request $request) {
    $request->validate([
        'documents'   => 'required|array|min:1|max:10',
        'documents.*' => 'required|file|mimes:pdf,jpg,jpeg,png|max:10240'
    ], [
        'documents.required'  => 'Sélectionnez au moins un fichier',
        'documents.max'       => 'Maximum 10 fichiers à la fois',
        'documents.*.mimes'   => 'Format accepté : PDF, JPG, PNG',
        'documents.*.max'     => 'Chaque fichier doit faire moins de 10 Mo',
    ]);

    $dataLakeClient = new DataLakeClient();
    $successCount   = 0;
    $errors         = [];

    foreach ($request->file('documents') as $fichier) {
        try {
            // 1. Stockage local
            $chemin = $fichier->store('documents', 'public');

            // 2. Sauvegarde en BDD
            Document::create([
                'nom_fichier_original' => $fichier->getClientOriginalName(),
                'chemin_stockage'      => $chemin,
                'type_document'        => 'non_classe',
                'statut_ocr'           => 'en_attente',
                'mime_type'            => $fichier->getMimeType(),
                'taille_fichier'       => $fichier->getSize(),
            ]);

            // 3. Envoi vers le Data Lake (RAW zone)
            try {
                $dataLakeClient->uploadRaw($fichier, $fichier->getClientOriginalName());
                Log::info('Document envoyé au Data Lake: ' . $fichier->getClientOriginalName());
            } catch (\Exception $e) {
                Log::error('Erreur envoi Data Lake: ' . $e->getMessage());
            }

            $successCount++;
        } catch (\Exception $e) {
            $errors[] = $fichier->getClientOriginalName() . ': ' . $e->getMessage();
        }
    }

    // 4. Déclencher le pipeline Airflow une seule fois
    if ($successCount > 0) {
        try {
            Http::timeout(5)->post('http://backend:8000/trigger-pipeline');
            Log::info('Pipeline Airflow déclenché après upload');
        } catch (\Exception $e) {
            Log::warning('Impossible de déclencher le pipeline: ' . $e->getMessage());
        }
    }

    $message = $successCount . ' fichier(s) uploadé(s) avec succès (pipeline déclenché)';
    if (!empty($errors)) {
        $message .= ' — ' . count($errors) . ' échec(s)';
    }

    return $successCount > 0
        ? redirect('/commercial/dashboard')->with('success', $message)
        : redirect('/commercial/dashboard')->with('error', 'Aucun fichier n\'a pu être uploadé');
})->name('upload');

// Routes commercial
Route::prefix('commercial')->group(function () {
    Route::get('/login', function () {
        return view('commercial.login', ['espace' => 'Commercial']);
    })->name('commercial.login');
    
    Route::post('/login', function (Illuminate\Http\Request $request) {
        $credentials = $request->validate([
            'email' => 'required|email',
            'password' => 'required'
        ]);

        if (Auth::attempt($credentials)) {
            $request->session()->regenerate();
            
            if (Auth::user()->role === 'commercial') {
                return redirect('/commercial/dashboard');
            }
            return redirect('/');
        }

        return back()->withErrors([
            'email' => 'Identifiants incorrects.',
        ]);
    });
    
    // DASHBOARD COMMERCIAL DYNAMIQUE
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
        
        // 3. Documents extraits par OCR (depuis la base de données)
        $documentsOCR = Extraction::with('document')
            ->latest()
            ->take(20)
            ->get()
            ->map(function ($extraction) {
                $donnees = $extraction->donnees_completes ?? [];
                return [
                    'document_type' => $donnees['document_type'] ?? $extraction->document->type_document ?? 'N/A',
                    'siret'         => $extraction->siret ?? ($donnees['entities']['siret'] ?? 'N/A'),
                    'tva'           => $extraction->taux_tva ?? ($donnees['financials']['tva'] ?? 'N/A'),
                    'date'          => $extraction->date_emission ?? ($donnees['entities']['dates'][0] ?? 'N/A'),
                    'montant_ht'    => $extraction->montant_ht ?? ($donnees['financials']['montant_ht'] ?? 0),
                    'montant_ttc'   => $extraction->montant_ttc ?? ($donnees['financials']['montant_ttc'] ?? 0),
                    'nom_fichier'   => $extraction->document->nom_fichier_original ?? '',
                ];
            })
            ->toArray();
        
        // 4. STATISTIQUES DYNAMIQUES
        $totalDocuments = Document::count();
        $documentsMois = Document::whereMonth('created_at', now()->month)
            ->whereYear('created_at', now()->year)
            ->count();
        $enAttente = Document::where('statut_ocr', 'en_attente')->count();
        $traites = Document::where('statut_ocr', 'traite')->count();
        
        return view('commercial.dashboard', [
            'documentsLocaux' => $documentsLocaux,
            'documentsCurated' => $documentsCurated,
            'documentsOCR' => $documentsOCR,
            'totalDocuments' => $totalDocuments,
            'documentsMois' => $documentsMois,
            'enAttente' => $enAttente,
            'traites' => $traites
        ]);
    })->name('commercial.dashboard');
});

// Routes conformité
Route::prefix('conformite')->group(function () {
    Route::get('/login', function () {
        return view('conformite.login', ['espace' => 'Conformité']);
    })->name('conformite.login');
    
    Route::post('/login', function (Illuminate\Http\Request $request) {
        $credentials = $request->validate([
            'email' => 'required|email',
            'password' => 'required'
        ]);

        if (Auth::attempt($credentials)) {
            $request->session()->regenerate();
            
            if (Auth::user()->role === 'conformite') {
                return redirect('/conformite/dashboard');
            }
            return redirect('/');
        }

        return back()->withErrors([
            'email' => 'Identifiants incorrects.',
        ]);
    });
    
    // DASHBOARD CONFORMITÉ DYNAMIQUE
    Route::get('/dashboard', function () {
        // 1. Documents traités : jointure Document + Extraction
        $documents = Document::with(['extraction', 'fournisseur'])
            ->where('statut_ocr', 'traite')
            ->latest()
            ->take(50)
            ->get();

        // 2. Alertes non résolues indexées par document_id
        $alertes = Alerte::where('resolue', false)
            ->latest('date_detection')
            ->get()
            ->keyBy(function ($alerte) {
                $ids = $alerte->documents_concerenes ?? [];
                return count($ids) > 0 ? $ids[0] : null;
            });

        // 3. Construire le tableau unifié pour la vue
        $documentsAdaptes = $documents->map(function ($doc) use ($alertes) {
            $extraction = $doc->extraction;
            $donnees    = $extraction ? ($extraction->donnees_completes ?? []) : [];
            $alerte     = $alertes->get($doc->id);

            $anomalies = [];
            if ($alerte) {
                $details   = $alerte->details ?? [];
                $anomalies = $details['anomalies'] ?? [];
            } elseif (!empty($donnees['validation']['anomalies'])) {
                $anomalies = $donnees['validation']['anomalies'];
            }

            $coherenceOk = empty($anomalies) && ($donnees['validation']['is_valid'] ?? true);

            return [
                'document_id'  => $doc->nom_fichier_original ?? $doc->id,
                'document_type'=> $donnees['document_type'] ?? $doc->type_document ?? 'inconnu',
                'fournisseur'  => $doc->fournisseur->nom ?? $extraction->nom_fournisseur ?? ($donnees['entities']['entreprise'] ?? 'Inconnu'),
                'siret'        => $extraction->siret ?? ($donnees['entities']['siret'] ?? 'N/A'),
                'montant_ttc'  => $extraction->montant_ttc ?? ($donnees['financials']['montant_ttc'] ?? 0),
                'coherence_ok' => $coherenceOk,
                'anomalies'    => $anomalies,
                'date_emission'=> $alerte ? $alerte->date_detection?->format('d/m/Y') : null,
            ];
        })->toArray();

        // 4. Stats
        $totalDocs     = count($documentsAdaptes);
        $conformes     = 0;
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

        return view('conformite.dashboard', [
            'documentsCurated' => $documentsAdaptes,
            'totalDocs'        => $totalDocs,
            'conformes'        => $conformes,
            'alertesRouges'    => $alertesRouges,
            'alertesOranges'   => $alertesOranges,
        ]);
    })->name('conformite.dashboard');
});

// Logout
Route::post('/logout', function (Illuminate\Http\Request $request) {
    Auth::logout();
    $request->session()->invalidate();
    $request->session()->regenerateToken();
    return redirect('/');
})->name('logout');