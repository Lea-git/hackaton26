<?php

use Illuminate\Support\Facades\Route;
use Illuminate\Support\Facades\Auth;
use Illuminate\Http\Request;
use App\Models\Document;
use Illuminate\Support\Facades\Storage;  
use App\Services\DataLakeClient;
use Illuminate\Support\Facades\Log;

// Page d'accueil
Route::get('/', function () {
    return view('welcome');
});

// Route d'upload
Route::post('/upload', function (Request $request) {
    $request->validate([
        'fichier' => 'required|file|mimes:pdf,jpg,jpeg,png|max:10240'
    ]);

    $fichier = $request->file('fichier');
    
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
            Log::info('Document envoyé au Data Lake pour OCR');
        }
    } catch (\Exception $e) {
        Log::error('Erreur envoi Data Lake: ' . $e->getMessage());
    }

    return redirect('/commercial/dashboard')->with('success', 'Fichier uploadé avec succès (en attente de traitement OCR)');
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
        
        // 3. Données de l'étudiant 2
        try {
            $jsonContent = Storage::disk('public')->get('test.json');
            $documentsOCR = json_decode($jsonContent, true) ?? [];
        } catch (\Exception $e) {
            $documentsOCR = [];
        }
        
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
    
    // DASHBOARD CONFORMITÉ DYNAMIQUE (adapté pour l'étudiant 5)
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
            // Adapte le format selon la structure de l'étudiant 5
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
        
        return view('conformite.dashboard', [
            'documentsCurated' => $documentsAdaptes,
            'totalDocs' => $totalDocs,
            'conformes' => $conformes,
            'alertesRouges' => $alertesRouges,
            'alertesOranges' => $alertesOranges
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