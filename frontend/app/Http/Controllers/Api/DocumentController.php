<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Document;
use App\Models\Extraction;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;


class DocumentController extends Controller
{
    // Liste tous les documents (avec filtre optionnel par nom_fichier)
    public function index(Request $request)
    {
        $query = Document::with('extraction', 'fournisseur');

        if ($request->has('nom_fichier')) {
            $query->where('nom_fichier_original', $request->nom_fichier);
        }

        $documents = $query->latest()->paginate(20);

        return response()->json([
            'success' => true,
            'data' => $documents
        ]);
    }

    // Créer un document (depuis Airflow, sans upload fichier)
    public function store(Request $request)
    {
        $request->validate([
            'nom_fichier_original' => 'required|string|max:255',
            'chemin_stockage' => 'required|string|max:500',
            'type_document' => 'required|string',
            'mime_type' => 'nullable|string|max:100',
            'taille_fichier' => 'nullable|integer',
        ]);

        $document = Document::create([
            'nom_fichier_original' => $request->nom_fichier_original,
            'chemin_stockage' => $request->chemin_stockage,
            'type_document' => $request->type_document,
            'statut_ocr' => 'en_attente',
            'mime_type' => $request->mime_type,
            'taille_fichier' => $request->taille_fichier,
        ]);

        return response()->json([
            'success' => true,
            'message' => 'Document enregistré',
            'data' => $document
        ], 201);
    }

    // Détail d'un document
    public function show($id)
    {
        $document = Document::with('extraction', 'fournisseur')
                            ->findOrFail($id);
        
        return response()->json([
            'success' => true,
            'data' => $document
        ]);
    }

    // Mettre à jour le type de document (après classification)
    public function updateType(Request $request, $id)
    {
        $request->validate([
            'type_document' => 'required|in:facture,devis,attestation,autre'
        ]);

        $document = Document::findOrFail($id);
        $document->type_document = $request->type_document;
        $document->save();

        return response()->json([
            'success' => true,
            'message' => 'Type de document mis à jour',
            'data' => $document
        ]);
    }

    // Obtenir le fichier
    public function download($id)
    {
        $document = Document::findOrFail($id);
        
        if (!Storage::disk('public')->exists($document->chemin_stockage)) {
            return response()->json([
                'success' => false,
                'message' => 'Fichier non trouvé'
            ], 404);
        }

        return response()->download(
            Storage::disk('public')->path($document->chemin_stockage),
            $document->nom_fichier_original
        );
    }
}