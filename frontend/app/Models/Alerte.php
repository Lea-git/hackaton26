<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Alerte extends Model
{
    protected $fillable = [
        'type',
        'niveau',
        'message',
        'documents_concerenes',
        'fournisseur_id',
        'details',
        'resolue',
        'date_detection',
        'date_resolution'
    ];

    protected $casts = [
        'documents_concerenes' => 'array',
        'details' => 'array',
        'resolue' => 'boolean',
        'date_detection' => 'datetime',
        'date_resolution' => 'datetime'
    ];

    public function fournisseur()
    {
        return $this->belongsTo(Fournisseur::class);
    }
}