<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Extraction extends Model
{
    protected $table = 'extractions';

    protected $fillable = [
        'document_id',
        'siren',
        'siret',
        'numero_tva',
        'montant_ht',
        'montant_ttc',
        'taux_tva',
        'date_emission',
        'date_echeance',
        'numero_facture',
        'nom_fournisseur',
        'adresse_fournisseur',
        'donnees_completes',
        'confiance_globale'
    ];

    protected $casts = [
        'donnees_completes' => 'array',
        'date_emission' => 'date',
        'date_echeance' => 'date',
        'montant_ht' => 'decimal:2',
        'montant_ttc' => 'decimal:2',
        'taux_tva' => 'decimal:2',
        'confiance_globale' => 'float'
    ];

    public function document()
    {
        return $this->belongsTo(Document::class);
    }
}