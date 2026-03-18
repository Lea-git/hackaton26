<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Document;
use App\Models\Extraction;
use Illuminate\Http\Request;

class ExtractionController extends Controller
{
    // Sauvegarder les données OCR pour un document
    public function store(Request $request, $documentId)
    {
        $request->validate([
            'siren' => 'nullable|string|size:9',
            'siret' => 'nullable|string|size:14',
            'montant_ttc' => 'nullable|numeric',
            'donnees_completes' => 'required|json',
            'confiance_globale' => 'required|numeric|min:0|max:100'
        ]);

        $document = Document::findOrFail($documentId);
        
        $extraction = Extraction::create([
            'document_id' => $documentId,
            'siren' => $request->siren,
            'siret' => $request->siret,
            'numero_tva' => $request->numero_tva,
            'montant_ht' => $request->montant_ht,
            'montant_ttc' => $request->montant_ttc,
            'taux_tva' => $request->taux_tva,
            'date_emission' => $request->date_emission,
            'date_echeance' => $request->date_echeance,
            'numero_facture' => $request->numero_facture,
            'nom_fournisseur' => $request->nom_fournisseur,
            'adresse_fournisseur' => $request->adresse_fournisseur,
            'donnees_completes' => json_decode($request->donnees_completes),
            'confiance_globale' => $request->confiance_globale
        ]);

        // Mettre à jour le statut du document
        $document->statut_ocr = 'traite';
        $document->extraction_id = $extraction->id;
        $document->save();

        return response()->json([
            'success' => true,
            'message' => 'Extraction sauvegardée',
            'data' => $extraction
        ], 201);
    }

    // Récupérer l'extraction d'un document
    public function show($documentId)
    {
        $extraction = Extraction::where('document_id', $documentId)->firstOrFail();
        
        return response()->json([
            'success' => true,
            'data' => $extraction
        ]);
    }
}