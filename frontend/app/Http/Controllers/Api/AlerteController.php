<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Alerte;
use Illuminate\Http\Request;

class AlerteController extends Controller
{
    public function index()
    {
        $alertes = Alerte::with('fournisseur')
                        ->where('resolue', false)
                        ->orderBy('date_detection', 'desc')
                        ->get();
        
        return response()->json([
            'success' => true,
            'data' => $alertes
        ]);
    }

    public function nonResolues()
    {
        $alertes = Alerte::with('fournisseur')
                        ->where('resolue', false)
                        ->orderBy('niveau', 'desc')
                        ->orderBy('date_detection', 'desc')
                        ->get();
        
        return response()->json([
            'success' => true,
            'data' => $alertes
        ]);
    }

    public function store(Request $request)
    {
        $request->validate([
            'type' => 'required|string',
            'niveau' => 'required|in:rouge,orange,vert',
            'message' => 'required|string',
            'documents_concerenes' => 'required|array',
            'fournisseur_id' => 'nullable|exists:fournisseurs,id',
            'details' => 'nullable|json'
        ]);

        $alerte = Alerte::create($request->all());

        return response()->json([
            'success' => true,
            'message' => 'Alerte créée',
            'data' => $alerte
        ], 201);
    }

    public function resoudre($id)
    {
        $alerte = Alerte::findOrFail($id);
        $alerte->resolue = true;
        $alerte->date_resolution = now();
        $alerte->save();

        return response()->json([
            'success' => true,
            'message' => 'Alerte résolue',
            'data' => $alerte
        ]);
    }
}