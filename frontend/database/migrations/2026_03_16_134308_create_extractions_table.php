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
    Schema::create('extractions', function (Blueprint $table) {
        $table->id();
        $table->foreignId('document_id')->constrained()->onDelete('cascade');
        $table->string('siren', 9)->nullable();
        $table->string('siret', 14)->nullable();
        $table->string('numero_tva')->nullable();
        $table->decimal('montant_ht', 10, 2)->nullable();
        $table->decimal('montant_ttc', 10, 2)->nullable();
        $table->decimal('taux_tva', 5, 2)->nullable();
        $table->date('date_emission')->nullable();
        $table->date('date_echeance')->nullable();
        $table->string('numero_facture')->nullable();
        $table->string('nom_fournisseur')->nullable();
        $table->string('adresse_fournisseur')->nullable();
        $table->json('donnees_completes');        // Tout ce qui a été extrait
        $table->float('confiance_globale');       // Score de confiance OCR (0-100)
        $table->timestamps();
    });
}

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('extracted_data');
    }
};
