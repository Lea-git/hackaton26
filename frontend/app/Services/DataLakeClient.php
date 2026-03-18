<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Storage;
use Aws\S3\S3Client;  
use Illuminate\Support\Facades\Log;

class DataLakeClient
{
    protected $baseUrl;
    protected $accessKey;
    protected $secretKey;
    
    public function __construct()
    {
        $this->baseUrl = env('MINIO_ENDPOINT', 'http://localhost:9000');
        $this->accessKey = env('MINIO_ACCESS_KEY', 'admin');
        $this->secretKey = env('MINIO_SECRET_KEY', 'admin1234');
    }
    
    public function getCuratedDocuments($prefix = '')
    {
        try {
            $response = Http::withBasicAuth($this->accessKey, $this->secretKey)
                ->get($this->baseUrl . '/curated-documents?prefix=' . $prefix);
                
            if ($response->successful()) {
                return $response->json();
            }
        } catch (\Exception $e) {
            return $this->getMockDocuments();
        }
        
        return $this->getMockDocuments();
    }
    
    public function getCuratedDocument($path)
    {
        try {
            $response = Http::withBasicAuth($this->accessKey, $this->secretKey)
                ->get($this->baseUrl . '/curated-documents/' . $path);
                
            if ($response->successful()) {
                return $response->json();
            }
        } catch (\Exception $e) {
            return null;
        }
        
        return null;
    }
    

   public function uploadRaw($fichier, $nomFichier)
{
    try {
        // Initialise le client S3
        $client = new S3Client([  // ← Plus besoin de \ devant
            'version' => 'latest',
            'region' => env('AWS_DEFAULT_REGION', 'us-east-1'),
            'endpoint' => env('AWS_ENDPOINT', 'http://localhost:9000'),
            'credentials' => [
                'key' => env('AWS_ACCESS_KEY_ID', 'admin'),
                'secret' => env('AWS_SECRET_ACCESS_KEY', 'admin1234'),
            ],
            'use_path_style_endpoint' => true,
        ]);

        // Upload vers le bucket raw-documents
        $result = $client->putObject([
            'Bucket' => 'raw-documents',
            'Key' => date('Y/m/d/') . $nomFichier,
            'Body' => fopen($fichier->getPathname(), 'r'),
            'ContentType' => $fichier->getMimeType(),
        ]);

        return $result['ObjectURL'] ?? true;
    } catch (\Exception $e) {
        Log::error('Erreur upload vers MinIO: ' . $e->getMessage());  // ← Plus besoin de \
        return false;
    }
}

public function getInvalidDocuments($prefix = '')
{
    try {
        // À adapter selon où l'étudiant 5 met les invalides
        $response = Http::withBasicAuth($this->accessKey, $this->secretKey)
            ->get($this->baseUrl . '/invalid-documents?prefix=' . $prefix);
            
        if ($response->successful()) {
            return $response->json();
        }
    } catch (\Exception $e) {
        return [];
    }
    
    return [];
}

    public function getMockDocuments()
    {
        return [
            [
                'document_id' => 'facture_acme_001',
                'document_type' => 'facture',
                'fournisseur' => 'ACME SAS',
                'siret' => '12345678900012',
                'date_emission' => '2026-03-15',
                'montant_ttc' => 1200.00,
                'coherence_ok' => true,
                'anomalies' => []
            ],
            [
                'document_id' => 'facture_dupont_002',
                'document_type' => 'facture',
                'fournisseur' => 'DUPONT SARL',
                'siret' => '98765432100045',
                'date_emission' => '2026-03-14',
                'montant_ttc' => 850.50,
                'coherence_ok' => true,
                'anomalies' => []
            ],
            [
                'document_id' => 'attestation_martin_001',
                'document_type' => 'attestation',
                'fournisseur' => 'MARTIN SAS',
                'siret' => '45678912300078',
                'date_emission' => '2026-01-10',
                'date_expiration' => '2026-12-31',
                'coherence_ok' => false,
                'anomalies' => ['Document expiré dans 3 mois']
            ]
        ];
    }
}