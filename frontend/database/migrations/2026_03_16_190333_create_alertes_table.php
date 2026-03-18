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
    Schema::create('alertes', function (Blueprint $table) {
        $table->id();
        $table->string('type');                    
        $table->enum('niveau', ['rouge', 'orange', 'vert'])->default('orange');
        $table->text('message');
        $table->json('documents_concerenes');       
        $table->foreignId('fournisseur_id')->nullable()->constrained();
        $table->json('details')->nullable();         // Données supplémentaires
        $table->boolean('resolue')->default(false);
        $table->timestamp('date_detection')->useCurrent();
        $table->timestamp('date_resolution')->nullable();
        $table->timestamps();
    });
}

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('alertes');
    }
};
