<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Fournisseur;
use App\Models\Document;
use Illuminate\Http\Request;

class FournisseurController extends Controller
{
    public function index()
    {
        $fournisseurs = Fournisseur::withCount('documents')
                                   ->orderBy('nom')
                                   ->get();
        
        return response()->json([
            'success' => true,
            'data' => $fournisseurs
        ]);
    }

    public function show($id)
    {
        $fournisseur = Fournisseur::with('documents.extraction')
                                  ->findOrFail($id);
        
        return response()->json([
            'success' => true,
            'data' => $fournisseur
        ]);
    }

    public function store(Request $request)
    {
        $request->validate([
            'nom' => 'required|string|max:255',
            'siren' => 'required|string|size:9|unique:fournisseurs',
            'siret' => 'nullable|string|size:14',
            'adresse' => 'nullable|string'
        ]);

        $fournisseur = Fournisseur::create($request->all());

        return response()->json([
            'success' => true,
            'message' => 'Fournisseur créé',
            'data' => $fournisseur
        ], 201);
    }

    public function update(Request $request, $id)
    {
        $fournisseur = Fournisseur::findOrFail($id);
        $fournisseur->update($request->all());

        return response()->json([
            'success' => true,
            'message' => 'Fournisseur mis à jour',
            'data' => $fournisseur
        ]);
    }
}