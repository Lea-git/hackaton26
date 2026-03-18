<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Document;
use App\Models\Alerte;
use Illuminate\Http\Request;

class VerificationController extends Controller
{
    public function verifierDocuments(Request $request)
    {
        $request->validate([
            'document_ids' => 'required|array',
            'document_ids.*' => 'exists:documents,id'
        ]);

        $documents = Document::with('extraction')
                            ->whereIn('id', $request->document_ids)
                            ->get();

        $alertes = [];

        // Regrouper par fournisseur potentiel (via SIREN)
        $documentsParSiren = $documents->groupBy(function ($doc) {
            return $doc->extraction->siren ?? 'inconnu';
        });

        foreach ($documentsParSiren as $siren => $docsDuGroupe) {
            // Règle 1: Cohérence des SIREN
            $sirens = $docsDuGroupe->pluck('extraction.siren')->filter()->unique();
            if ($sirens->count() > 1) {
                $alertes[] = Alerte::create([
                    'type' => 'siren_mismatch',
                    'niveau' => 'rouge',
                    'message' => 'SIREN différents entre les documents',
                    'documents_concerenes' => $docsDuGroupe->pluck('id'),
                    'details' => ['sirens' => $sirens]
                ]);
            }

            // Règle 2: TVA cohérente
            $factures = $docsDuGroupe->where('type_document', 'facture');
            foreach ($factures as $facture) {
                $extract = $facture->extraction;
                if ($extract && $extract->montant_ht && $extract->montant_ttc && $extract->taux_tva) {
                    $ttcCalcule = $extract->montant_ht * (1 + $extract->taux_tva / 100);
                    if (abs($ttcCalcule - $extract->montant_ttc) > 0.01) {
                        $alertes[] = Alerte::create([
                            'type' => 'tva_incoherente',
                            'niveau' => 'orange',
                            'message' => 'TVA incohérente sur la facture',
                            'documents_concerenes' => [$facture->id],
                            'details' => [
                                'ht' => $extract->montant_ht,
                                'ttc' => $extract->montant_ttc,
                                'taux' => $extract->taux_tva
                            ]
                        ]);
                    }
                }
            }

            // Règle 3: Dates d'expiration
            $attestations = $docsDuGroupe->where('type_document', 'attestation');
            foreach ($attestations as $attestation) {
                if ($attestation->extraction && $attestation->extraction->date_echeance) {
                    if ($attestation->extraction->date_echeance < now()) {
                        $alertes[] = Alerte::create([
                            'type' => 'document_expire',
                            'niveau' => 'orange',
                            'message' => 'Attestation expirée',
                            'documents_concerenes' => [$attestation->id],
                            'details' => [
                                'date_expiration' => $attestation->extraction->date_echeance
                            ]
                        ]);
                    }
                }
            }
        }

        return response()->json([
            'success' => true,
            'message' => count($alertes) . ' incohérence(s) détectée(s)',
            'data' => $alertes
        ]);
    }

    public function verifierFournisseur($fournisseurId)
    {
        $documents = Document::where('fournisseur_id', $fournisseurId)
                            ->with('extraction')
                            ->get();

        return $this->verifierDocuments(
            new Request(['document_ids' => $documents->pluck('id')->toArray()])
        );
    }
}