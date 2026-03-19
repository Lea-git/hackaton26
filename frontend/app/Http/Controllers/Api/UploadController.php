<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use App\Models\Document;
use Aws\S3\S3Client;
use Aws\Exception\AwsException;

class UploadController extends Controller
{
    private function makeS3Client(): S3Client
    {
        return new S3Client([
            'version'                 => 'latest',
            'region'                  => 'us-east-1',
            'endpoint'                => env('MINIO_ENDPOINT', 'http://minio:9000'),
            'use_path_style_endpoint' => true,
            'credentials'             => [
                'key'    => env('MINIO_ACCESS_KEY', 'admin'),
                'secret' => env('MINIO_SECRET_KEY', 'admin1234'),
            ],
        ]);
    }

    private function triggerAirflow(string $filename): void
    {
        $url      = rtrim(env('AIRFLOW_API_URL', 'http://airflow-webserver:8080'), '/');
        $user     = env('AIRFLOW_USER', 'admin');
        $password = env('AIRFLOW_PASSWORD', 'admin');

        Http::timeout(10)
            ->withBasicAuth($user, $password)
            ->post("{$url}/api/v1/dags/docuhack_document_pipeline/dagRuns", [
                'conf' => [
                    'triggered_by' => 'frontend_upload',
                    'filename'     => $filename,
                ],
            ]);
    }

    public function upload(Request $request)
    {
        $request->validate([
            'documents.*' => 'required|file|mimes:pdf,jpg,jpeg,png|max:10240',
        ]);

        $s3        = $this->makeS3Client();
        $documents = [];

        foreach ($request->file('documents') as $file) {
            $filename = $file->getClientOriginalName();

            // 1. Upload dans MinIO (raw-documents)
            try {
                $s3->putObject([
                    'Bucket'      => 'raw-documents',
                    'Key'         => $filename,
                    'Body'        => fopen($file->getRealPath(), 'rb'),
                    'ContentType' => $file->getMimeType(),
                ]);
            } catch (AwsException $e) {
                Log::error("MinIO upload failed for {$filename}: {$e->getMessage()}");
                continue;
            }

            // 2. Créer l'entrée en BDD (statut en_attente, Airflow mettra à jour)
            $document = Document::create([
                'nom_fichier_original' => $filename,
                'chemin_stockage'      => "raw-documents/{$filename}",
                'mime_type'            => $file->getMimeType(),
                'taille_fichier'       => $file->getSize(),
                'statut_ocr'           => 'en_attente',
                'type_document'        => 'non_classe',
            ]);

            // 3. Déclencher le pipeline Airflow
            try {
                $this->triggerAirflow($filename);
                Log::info("Airflow DAG déclenché pour {$filename}");
            } catch (\Exception $e) {
                Log::warning("Airflow trigger failed for {$filename}: {$e->getMessage()}");
            }

            $documents[] = $document;
        }

        return response()->json([
            'success' => true,
            'message' => count($documents) . ' document(s) uploadé(s) — traitement en cours',
            'data'    => $documents,
        ], 201);
    }

    public function uploadProgress(Request $request)
    {
        // Pour gérer l'upload progressif si nécessaire
        return response()->json([
            'success' => true,
            'message' => 'Upload en cours...'
        ]);
    }
}