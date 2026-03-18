<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use App\Models\Document;

class UploadController extends Controller
{
    public function upload(Request $request)
    {
        $request->validate([
            'documents.*' => 'required|file|mimes:pdf,jpg,jpeg,png|max:10240', // 10MB max
        ]);

        $documents = [];

        foreach ($request->file('documents') as $file) {
            // Stocker le fichier
            $path = $file->store('uploads/' . date('Y/m/d'), 'public');
            
            // Créer l'entrée en BDD
            $document = Document::create([
                'nom_fichier_original' => $file->getClientOriginalName(),
                'chemin_stockage' => $path,
                'mime_type' => $file->getMimeType(),
                'taille_fichier' => $file->getSize(),
                'statut_ocr' => 'en_attente',
                'type_document' => 'non_classe'
            ]);
            
            $documents[] = $document;
        }

        return response()->json([
            'success' => true,
            'message' => count($documents) . ' document(s) uploadé(s) avec succès',
            'data' => $documents
        ], 201);
    }

    public function uploadProgress(Request $request)
    {
        // Pour gérer l'upload progressif si nécessaire
        return response()->json([
            'success' => true,
            'message' => 'Upload en cours...'
        ]);
    }
}