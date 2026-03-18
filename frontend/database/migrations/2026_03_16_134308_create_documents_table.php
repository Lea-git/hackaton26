<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    
    public function up()
    {
    Schema::create('documents', function (Blueprint $table) {
        $table->id();
        $table->string('nom_fichier_original');
        $table->string('chemin_stockage');      // Où est stocké le fichier
        $table->string('type_document');         // facture, devis, attestation
        $table->string('statut_ocr')->default('en_attente'); // en_attente, traite, erreur
        $table->json('donnees_brutes_ocr')->nullable(); // Tout le texte extrait par OCR
        $table->string('mime_type');              // application/pdf, image/jpeg
        $table->integer('taille_fichier');        // en octets
        $table->foreignId('extraction_id')->nullable()->constrained();
        $table->foreignId('fournisseur_id')->nullable()->constrained();
        $table->timestamps();
    });
    }
    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('documents');
    }
};
