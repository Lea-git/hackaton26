<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use App\Models\Document; 

class DocumentSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run()
{
    Document::create([
        'nom_fichier_original' => 'facture_test.pdf',
        'chemin_stockage' => 'documents/facture_test.pdf',
        'type_document' => 'facture',
        'statut_ocr' => 'traite',
        'mime_type' => 'application/pdf',
        'taille_fichier' => 1024
    ]);
}
}
