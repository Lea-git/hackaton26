<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Fournisseur extends Model
{
    protected $fillable = [
        'nom',
        'siren',
        'siret',
        'numero_tva',
        'adresse',
        'code_postal',
        'ville',
        'email_contact',
        'telephone',
        'statut',
        'total_facture_annuel',
        'nombre_factures',
        'derniere_facture'
    ];

    protected $casts = [
        'total_facture_annuel' => 'decimal:2',
        'derniere_facture' => 'date'
    ];

    public function documents()
    {
        return $this->hasMany(Document::class);
    }

    public function alertes()
    {
        return $this->hasMany(Alerte::class);
    }
}