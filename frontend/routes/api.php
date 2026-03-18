<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\Api\UploadController;
use App\Http\Controllers\Api\DocumentController;
use App\Http\Controllers\Api\ExtractionController;
use App\Http\Controllers\Api\FournisseurController;
use App\Http\Controllers\Api\AlerteController;
use App\Http\Controllers\Api\VerificationController;

// Upload
Route::post('/upload', [UploadController::class, 'upload']);
Route::post('/upload/progress', [UploadController::class, 'uploadProgress']);

// Documents
Route::get('/documents', [DocumentController::class, 'index']);
Route::post('/documents', [DocumentController::class, 'store']);
Route::get('/documents/{id}', [DocumentController::class, 'show']);
Route::patch('/documents/{id}/type', [DocumentController::class, 'updateType']);
Route::get('/documents/{id}/download', [DocumentController::class, 'download']);

// Extractions OCR
Route::post('/documents/{documentId}/extractions', [ExtractionController::class, 'store']);
Route::get('/documents/{documentId}/extractions', [ExtractionController::class, 'show']);

// Fournisseurs
Route::get('/fournisseurs', [FournisseurController::class, 'index']);
Route::get('/fournisseurs/{id}', [FournisseurController::class, 'show']);
Route::post('/fournisseurs', [FournisseurController::class, 'store']);
Route::put('/fournisseurs/{id}', [FournisseurController::class, 'update']);

// Alertes
Route::get('/alertes', [AlerteController::class, 'index']);
Route::get('/alertes/non-resolues', [AlerteController::class, 'nonResolues']);
Route::post('/alertes', [AlerteController::class, 'store']);
Route::patch('/alertes/{id}/resoudre', [AlerteController::class, 'resoudre']);

// Vérifications
Route::post('/verifier/documents', [VerificationController::class, 'verifierDocuments']);
Route::get('/verifier/fournisseurs/{fournisseurId}', [VerificationController::class, 'verifierFournisseur']);