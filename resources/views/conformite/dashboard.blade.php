<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Conformité - DocuHack</title>
    @vite(['resources/css/app.css'])
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', 'Segoe UI', sans-serif;
            background: #f3f4f6;
        }
        .navbar {
            background: white;
            padding: 1rem 2rem;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .logo {
            font-size: 1.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .user-info {
            display: flex;
            align-items: center;
            gap: 1.5rem;
        }
        .logout {
            padding: 0.5rem 1.25rem;
            background: #ef4444;
            color: white;
            border-radius: 8px;
            text-decoration: none;
        }
        .container {
            padding: 2rem;
            max-width: 1600px;
            margin: 0 auto;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        .stat-card {
            background: white;
            padding: 1.5rem;
            border-radius: 16px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
            border-left: 4px solid;
        }
        .stat-card.rouge { border-left-color: #ef4444; }
        .stat-card.orange { border-left-color: #f59e0b; }
        .stat-card.vert { border-left-color: #10b981; }
        .stat-card.bleu { border-left-color: #3b82f6; }
        .stat-card h3 {
            color: #6b7280;
            font-size: 0.875rem;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
        }
        .stat-card .value {
            font-size: 2rem;
            font-weight: 700;
            color: #1f2937;
        }
        .alertes-list {
            display: flex;
            flex-direction: column;
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .alerte-card {
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
            display: flex;
            align-items: flex-start;
            gap: 1rem;
            border-left: 4px solid;
        }
        .alerte-card.rouge { border-left-color: #ef4444; }
        .alerte-card.orange { border-left-color: #f59e0b; }
        .alerte-card.vert { border-left-color: #10b981; }
        .alerte-icon { font-size: 1.5rem; }
        .alerte-content { flex: 1; }
        .alerte-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.5rem;
        }
        .alerte-title { font-weight: 600; }
        .alerte-date { color: #6b7280; font-size: 0.9rem; }
        .alerte-message { color: #4b5563; margin-bottom: 0.75rem; }
        .alerte-details {
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
            font-size: 0.9rem;
            color: #6b7280;
        }
        .badge {
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .badge-siret { background: #fee2e2; color: #b91c1c; }
        .badge-tva { background: #fed7aa; color: #92400e; }
        .badge-nom { background: #dbeafe; color: #1e40af; }
        .badge-fraude { background: #fecaca; color: #7f1d1d; }
        .badge-success { background: #d1fae5; color: #065f46; }
        .table-wrapper {
            overflow-x: auto;
            border-radius: 12px;
            background: white;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th {
            background: #f9fafb;
            padding: 1rem;
            text-align: left;
            color: #4b5563;
            font-weight: 600;
            border-bottom: 2px solid #e5e7eb;
        }
        td {
            padding: 1rem;
            border-bottom: 1px solid #f3f4f6;
        }
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="logo"> DocuHack Conformité</div>
        <div class="user-info">
            <span>👤 conformite@docuhack.com</span>
            <a href="/conformite/login" class="logout">Déconnexion</a>
        </div>
    </nav>

    <div class="container">
        <!-- Statistiques dynamiques -->
        <div class="stats-grid">
            <div class="stat-card vert">
                <h3>Documents conformes</h3>
                <div class="value">{{ $conformes }}</div>
            </div>
            <div class="stat-card orange">
                <h3>Alertes orange</h3>
                <div class="value">{{ $alertesOranges }}</div>
            </div>
            <div class="stat-card rouge">
                <h3>Alertes rouges</h3>
                <div class="value">{{ $alertesRouges }}</div>
            </div>
            <div class="stat-card bleu">
                <h3>Total documents</h3>
                <div class="value">{{ $totalDocs }}</div>
            </div>
        </div>

        <!-- Liste des alertes dynamique -->
        <h2 class="text-xl font-bold mb-4">Alertes de conformité</h2>
        <div class="alertes-list">
            @forelse($documentsCurated as $doc)
                @if(!($doc['coherence_ok'] ?? true))
                    <div class="alerte-card {{ isset($doc['anomalies']) && count($doc['anomalies']) > 1 ? 'rouge' : 'orange' }}">
                        <div class="alerte-icon">{{ isset($doc['anomalies']) && count($doc['anomalies']) > 1 ? '🔴' : '🟠' }}</div>
                        <div class="alerte-content">
                            <div class="alerte-header">
                                <span class="alerte-title">{{ $doc['document_type'] ?? 'Document' }} - {{ $doc['fournisseur'] ?? 'Inconnu' }}</span>
                                <span class="alerte-date">{{ $doc['date_emission'] ?? 'Date inconnue' }}</span>
                            </div>
                            <div class="alerte-message">
                                @if(!empty($doc['anomalies']))
                                    {{ implode(', ', $doc['anomalies']) }}
                                @else
                                    Anomalie détectée
                                @endif
                            </div>
                            <div class="alerte-details">
                                <span class="badge badge-siret">SIRET: {{ $doc['siret'] ?? 'N/A' }}</span>
                            </div>
                        </div>
                    </div>
                @endif
            @empty
                <p class="text-gray-500 text-center py-4">Aucune alerte pour le moment</p>
            @endforelse
        </div>

        <!-- Tableau récapitulatif dynamique -->
        <h2 class="text-xl font-bold mb-4 mt-8">Derniers documents analysés</h2>
        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th>Document</th>
                        <th>Fournisseur</th>
                        <th>SIRET</th>
                        <th>Montant TTC</th>
                        <th>Statut</th>
                        <th>Anomalies</th>
                    </tr>
                </thead>
                <tbody>
                    @forelse($documentsCurated as $doc)
                    <tr class="border-t">
                        <td>{{ $doc['document_id'] ?? 'N/A' }}</td>
                        <td>{{ $doc['fournisseur'] ?? 'N/A' }}</td>
                        <td class="font-mono">{{ $doc['siret'] ?? 'N/A' }}</td>
                        <td class="montant">{{ isset($doc['montant_ttc']) ? number_format($doc['montant_ttc'], 0) : 'N/A' }} €</td>
                        <td>
                            @if($doc['coherence_ok'] ?? false)
                                <span class="badge badge-success">OK</span>
                            @else
                                <span class="badge {{ isset($doc['anomalies']) && count($doc['anomalies']) > 1 ? 'badge-fraude' : 'badge-tva' }}">
                                    {{ isset($doc['anomalies']) && count($doc['anomalies']) > 1 ? 'FRAUDE' : 'Anomalie' }}
                                </span>
                            @endif
                        </td>
                        <td>
                            @if(!empty($doc['anomalies']))
                                {{ implode(', ', array_slice($doc['anomalies'], 0, 2)) }}
                                @if(count($doc['anomalies']) > 2) ... @endif
                            @else
                                <span class="text-green-600">Aucune</span>
                            @endif
                        </td>
                    </tr>
                    @empty
                    <tr>
                        <td colspan="6" class="text-center py-4 text-gray-500">
                            Aucun document analysé
                        </td>
                    </tr>
                    @endforelse
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>