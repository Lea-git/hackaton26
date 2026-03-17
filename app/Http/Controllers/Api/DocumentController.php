<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Document;
use App\Models\Extraction;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;


class DocumentController extends Controller
{
    // Liste tous les documents
    public function index()
    {
        $documents = Document::with('extraction', 'fournisseur')
                            ->latest()
                            ->paginate(20);
        
        return response()->json([
            'success' => true,
            'data' => $documents
        ]);
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