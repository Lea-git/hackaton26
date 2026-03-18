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
    Schema::create('fournisseurs', function (Blueprint $table) {
        $table->id();
        $table->string('nom');
        $table->string('siren', 9)->unique();
        $table->string('siret', 14)->nullable();
        $table->string('numero_tva')->nullable();
        $table->string('adresse')->nullable();
        $table->string('code_postal', 5)->nullable();
        $table->string('ville')->nullable();
        $table->string('email_contact')->nullable();
        $table->string('telephone')->nullable();
        $table->enum('statut', ['actif', 'inactif', 'a_verifier'])->default('actif');
        $table->decimal('total_facture_annuel', 10, 2)->default(0);
        $table->integer('nombre_factures')->default(0);
        $table->date('derniere_facture')->nullable();
        $table->timestamps();
    });
}


    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('fournisseurs');
    }
};
