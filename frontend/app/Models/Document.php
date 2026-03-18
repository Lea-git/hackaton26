<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Document extends Model
{
    protected $fillable = [
        'nom_fichier_original',
        'chemin_stockage',
        'type_document',
        'statut_ocr',
        'donnees_brutes_ocr',
        'mime_type',
        'taille_fichier',
        'extraction_id',
        'fournisseur_id'
    ];

    protected $casts = [
        'donnees_brutes_ocr' => 'array',
        'taille_fichier' => 'integer'
    ];

    public function extraction()
    {
        return $this->belongsTo(Extraction::class);
    }

    public function fournisseur()
    {
        return $this->belongsTo(Fournisseur::class);
    }
}