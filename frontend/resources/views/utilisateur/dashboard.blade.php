<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CRM Commercial - DocuHack</title>
    @vite(['resources/sass/app.scss', 'resources/js/app.js'])
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f3f4f6;
        }
        
        /* Navbar */
        .navbar {
            background: white;
            padding: 1rem 2rem;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .logo {
            font-size: 1.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .user-info {
            display: flex;
            align-items: center;
            gap: 1.5rem;
        }
        .user-info span {
            color: #4b5563;
            font-weight: 500;
        }
        .logout {
            padding: 0.5rem 1.25rem;
            background: #ef4444;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            text-decoration: none;
            font-size: 0.9rem;
            font-weight: 500;
            transition: all 0.2s;
        }
        .logout:hover {
            background: #dc2626;
            transform: translateY(-1px);
            box-shadow: 0 4px 6px -1px rgba(239, 68, 68, 0.3);
        }
        
        /* Container */
        .container {
            padding: 2rem;
            max-width: 1600px;
            margin: 0 auto;
        }
        
        /* Messages */
        .alert-success {
            background: #d1fae5;
            border: 1px solid #a7f3d0;
            color: #065f46;
            padding: 1rem 1.5rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            box-shadow: 0 2px 4px rgba(5, 150, 105, 0.1);
        }
        .alert-success:before {
            content: "✓";
            background: #10b981;
            color: white;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
        }
        
        /* Sections */
        .section-card {
            background: white;
            border-radius: 16px;
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05);
            padding: 1.5rem;
            margin-bottom: 2rem;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .section-card:hover {
            box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1), 0 10px 10px -5px rgba(0,0,0,0.04);
        }
        
        .section-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding-bottom: 0.75rem;
            border-bottom: 2px solid #e5e7eb;
        }
        .section-title-icon {
            width: 32px;
            height: 32px;
            background: #e5e7eb;
            border-radius: 10px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 1.1rem;
        }
        
        /* Upload section */
        .upload-section {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2rem;
            border-radius: 20px;
            margin-bottom: 2rem;
            color: white;
            box-shadow: 0 20px 25px -5px rgba(102, 126, 234, 0.3), 0 10px 10px -5px rgba(0,0,0,0.04);
        }
        .upload-section h3 {
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 1.5rem;
            color: white;
            border-bottom: none;
        }
        .upload-section form {
            background: rgba(255,255,255,0.15);
            backdrop-filter: blur(10px);
            padding: 1.5rem;
            border-radius: 16px;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .upload-section button {
            background: white;
            color: #667eea;
            font-weight: 600;
            padding: 0.75rem 2rem;
            border-radius: 10px;
            border: none;
            cursor: pointer;
            transition: all 0.2s;
        }
        .upload-section button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.2);
        }
        .drop-zone {
            background: rgba(255,255,255,0.9);
            border: 2px dashed #a5b4fc;
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
            color: #4b5563;
        }
        .drop-zone:hover, .drop-zone.drag-over {
            border-color: #667eea;
            background: #f5f3ff;
        }
        #file-list {
            margin-top: 0.75rem;
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
            max-height: 160px;
            overflow-y: auto;
        }
        .file-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(255,255,255,0.85);
            border-radius: 8px;
            padding: 0.4rem 0.75rem;
            font-size: 0.82rem;
            color: #1f2937;
        }
        .file-item button {
            background: #ef4444;
            color: white;
            border: none;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            font-size: 0.7rem;
            cursor: pointer;
            padding: 0;
            line-height: 20px;
            font-weight: 700;
            flex-shrink: 0;
            transition: background 0.15s;
        }
        .file-item button:hover {
            background: #dc2626;
            transform: none;
            box-shadow: none;
        }
        #upload-submit {
            margin-top: 1rem;
        }
        #upload-progress {
            margin-top: 0.75rem;
            font-size: 0.85rem;
            color: white;
            font-weight: 500;
            display: none;
        }
        
        /* Stats */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        .stat-card {
            background: white;
            padding: 1.5rem;
            border-radius: 16px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
            border-left: 4px solid #10b981;
            transition: all 0.2s;
        }
        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
        }
        .stat-card h3 {
            color: #6b7280;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
        }
        .stat-card .value {
            font-size: 2rem;
            font-weight: 700;
            color: #1f2937;
        }
        
        /* Tables */
        .table-wrapper {
            overflow-x: auto;
            border-radius: 12px;
            background: white;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            min-width: 600px;
        }
        th {
            background: #f9fafb;
            padding: 1rem 1.5rem;
            text-align: left;
            color: #4b5563;
            font-weight: 600;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-bottom: 2px solid #e5e7eb;
        }
        td {
            padding: 1rem 1.5rem;
            border-bottom: 1px solid #f3f4f6;
            color: #1f2937;
        }
        tr:hover {
            background: #f9fafb;
        }
        
        /* Badges */
        .badge {
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.025em;
        }
        .badge-success {
            background: #d1fae5;
            color: #065f46;
        }
        .badge-warning {
            background: #fed7aa;
            color: #92400e;
        }
        .badge-danger {
            background: #fee2e2;
            color: #b91c1c;
        }
        .badge-info {
            background: #dbeafe;
            color: #1e40af;
        }
        
        /* Couleurs de section */
        .section-ocr { border-top: 4px solid #8b5cf6; }
        .section-recent { border-top: 4px solid #10b981; }
        .section-datalake { border-top: 4px solid #f59e0b; }
        .section-fournisseurs { border-top: 4px solid #ef4444; }
        
        /* Montants */
        .montant {
            font-weight: 600;
            color: #059669;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .container { padding: 1rem; }
            .stats-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="logo">📊 DocuHack CRM</div>
        <div class="user-info">
            <span>👤 commercial@docuhack.com</span>
            <a href="/utilisateur/login" class="logout">Déconnexion</a>
        </div>
    </nav>

    <div class="container">
        <!-- Message de succès -->
        @if(session('success'))
            <div class="alert-success">
                {{ session('success') }}
            </div>
        @endif

        <!-- Upload Section -->
        <div class="upload-section">
            <h3>⬆️ Uploader des documents <span style="font-size:0.85rem;font-weight:400;color:#6b7280;">(multi-fichiers supporté)</span></h3>
            @if(session('success'))
                <div style="margin-bottom:0.75rem;color:#065f46;background:#d1fae5;padding:0.75rem 1rem;border-radius:8px;font-size:0.9rem;font-weight:500;">
                    ✓ {{ session('success') }}
                </div>
            @endif
            @if(session('error'))
                <div style="margin-bottom:0.75rem;color:#991b1b;background:#fee2e2;padding:0.75rem 1rem;border-radius:8px;font-size:0.9rem;font-weight:500;">
                    ✗ {{ session('error') }}
                </div>
            @endif
            <div>
                <input type="file" id="fichier-hidden" accept=".pdf,.jpg,.jpeg,.png" multiple style="display:none">
                <div class="drop-zone" id="drop-zone" onclick="document.getElementById('fichier-hidden').click()">
                    <div style="font-size:2rem;margin-bottom:0.5rem;">📎</div>
                    <div style="font-weight:600;color:#4b5563;">Cliquez ou glissez vos fichiers ici</div>
                    <div style="font-size:0.8rem;color:#6b7280;margin-top:0.25rem;">PDF, JPG, PNG — max 50 Mo par fichier</div>
                </div>
                <div id="file-list"></div>
                <div id="upload-progress">⏳ Upload en cours...</div>
                <button type="button" id="upload-submit" onclick="submitFiles()" style="display:none">
                    ⬆️ Uploader <span id="upload-count"></span>
                </button>
            </div>
            <script>
                const dt = new DataTransfer();
                const hiddenInput = document.getElementById('fichier-hidden');
                const dropZone = document.getElementById('drop-zone');
                const fileList = document.getElementById('file-list');
                const submitBtn = document.getElementById('upload-submit');
                const uploadCount = document.getElementById('upload-count');
                const progressEl = document.getElementById('upload-progress');

                function addFiles(files) {
                    for (const f of files) {
                        // Avoid duplicates by name+size
                        let exists = false;
                        for (const existing of dt.files) {
                            if (existing.name === f.name && existing.size === f.size) { exists = true; break; }
                        }
                        if (!exists) dt.items.add(f);
                    }
                    renderList();
                }

                function renderList() {
                    fileList.innerHTML = '';
                    for (let i = 0; i < dt.files.length; i++) {
                        const f = dt.files[i];
                        const item = document.createElement('div');
                        item.className = 'file-item';
                        item.innerHTML = `<span>📄 ${f.name} <span style="color:#9ca3af;">(${(f.size/1024/1024).toFixed(2)} Mo)</span></span>`;
                        const removeBtn = document.createElement('button');
                        removeBtn.textContent = '×';
                        removeBtn.title = 'Supprimer';
                        removeBtn.onclick = () => { dt.items.remove(i); renderList(); };
                        item.appendChild(removeBtn);
                        fileList.appendChild(item);
                    }
                    const n = dt.files.length;
                    if (n > 0) {
                        submitBtn.style.display = 'inline-block';
                        uploadCount.textContent = n + ' fichier' + (n > 1 ? 's' : '');
                    } else {
                        submitBtn.style.display = 'none';
                    }
                }

                hiddenInput.addEventListener('change', function() {
                    addFiles(this.files);
                    this.value = ''; // reset so same file can be re-added later
                });

                // Drag & drop
                dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
                dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
                dropZone.addEventListener('drop', e => {
                    e.preventDefault();
                    dropZone.classList.remove('drag-over');
                    addFiles(e.dataTransfer.files);
                });

                function submitFiles() {
                    if (dt.files.length === 0) return;
                    const formData = new FormData();
                    formData.append('_token', '{{ csrf_token() }}');
                    for (const f of dt.files) {
                        formData.append('documents[]', f);
                    }
                    submitBtn.disabled = true;
                    progressEl.style.display = 'block';
                    fetch('{{ route("upload") }}', { method: 'POST', body: formData })
                        .then(r => { window.location.href = r.url || '/utilisateur/dashboard'; })
                        .catch(() => { window.location.reload(); });
                }
            </script>
        </div>

        <!-- Statistiques DYNAMIQUES -->
        <div class="stats-grid">
            <div class="stat-card">
                <h3>Documents total</h3>
                <div class="value">{{ $totalDocuments }}</div>
            </div>
            <div class="stat-card">
                <h3>Uploads ce mois</h3>
                <div class="value">{{ $documentsMois }}</div>
            </div>
            <div class="stat-card">
                <h3>Traités</h3>
                <div class="value">{{ $traites }}</div>
            </div>
            <div class="stat-card">
                <h3>En attente</h3>
                <div class="value">{{ $enAttente }}</div>
            </div>
        </div>

        <!-- Documents OCR -->
        <div class="section-card section-ocr">
            <div class="section-title">
                <span class="section-title-icon">🔍</span>
                Documents extraits par OCR
            </div>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Type</th>
                            <th>SIRET</th>
                            <th>TVA</th>
                            <th>Date</th>
                            <th>Montant HT</th>
                            <th>Montant TTC</th>
                        </tr>
                    </thead>
                    <tbody>
                        @forelse($documentsOCR as $doc)
                        <tr>
                            <td><span class="badge badge-info">{{ $doc['document_type'] ?? 'N/A' }}</span></td>
                            <td>{{ $doc['siret'] ?? 'N/A' }}</td>
                            <td>{{ $doc['tva'] ?? 'N/A' }}</td>
                            <td>{{ $doc['date'] ?? 'N/A' }}</td>
                            <td class="montant">{{ isset($doc['montant_ht']) ? number_format($doc['montant_ht'], 2) : 'N/A' }} €</td>
                            <td class="montant">{{ isset($doc['montant_ttc']) ? number_format($doc['montant_ttc'], 2) : 'N/A' }} €</td>
                        </tr>
                        @empty
                        <tr>
                            <td colspan="6" class="text-center py-8 text-gray-500">
                                Aucune donnée OCR disponible
                            </td>
                        </tr>
                        @endforelse
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Documents récents -->
        <div class="section-card section-recent">
            <div class="section-title">
                <span class="section-title-icon">📄</span>
                Documents récents
            </div>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Nom du fichier</th>
                            <th>Type</th>
                            <th>Date d'upload</th>
                            <th>Statut OCR</th>
                            <th>Visualiser</th>
                        </tr>
                    </thead>
                    <tbody>
                        @forelse($documentsLocaux as $doc)
                        <tr>
                            <td>{{ $doc->nom_fichier_original }}</td>
                            <td><span class="badge badge-info">{{ $doc->type_document }}</span></td>
                            <td>{{ $doc->created_at->format('d/m/Y H:i') }}</td>
                            <td>
                                <span class="badge {{
                                    $doc->statut_ocr === 'traite' ? 'badge-success' :
                                    ($doc->statut_ocr === 'erreur' ? 'badge-danger' : 'badge-warning')
                                }}">
                                    {{ $doc->statut_ocr }}
                                </span>
                            </td>
                            <td>
                                @php
                                    $chemin = $doc->chemin_stockage ?? '';
                                    $url = str_starts_with($chemin, 'raw-documents/')
                                        ? 'http://localhost:9000/' . $chemin
                                        : asset('storage/' . $chemin);
                                @endphp
                                <a href="{{ $url }}" target="_blank" style="color:#3b82f6;text-decoration:underline;font-size:0.875rem;">
                                    Voir le fichier
                                </a>
                            </td>
                        </tr>
                        @empty
                        <tr>
                            <td colspan="5" class="text-center py-8 text-gray-500">
                                Aucun document pour le moment
                            </td>
                        </tr>
                        @endforelse
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Documents Data Lake -->
        <div class="section-card section-datalake">
            <div class="section-title">
                <span class="section-title-icon">🏢</span>
                Documents analysés
            </div>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Document</th>
                            <th>Type</th>
                            <th>Fournisseur</th>
                            <th>SIRET</th>
                            <th>Montant TTC</th>
                            <th>Cohérence</th>
                        </tr>
                    </thead>
                    <tbody>
                        @forelse($documentsCurated as $doc)
                        <tr>
                            <td>{{ $doc['document_id'] ?? 'N/A' }}</td>
                            <td><span class="badge badge-info">{{ $doc['document_type'] ?? 'N/A' }}</span></td>
                            <td>{{ $doc['fournisseur'] ?? 'N/A' }}</td>
                            <td>{{ $doc['siret'] ?? 'N/A' }}</td>
                            <td class="montant">
                                @if(isset($doc['montant_ttc']))
                                    {{ number_format($doc['montant_ttc'], 2) }} €
                                @elseif(isset($doc['montant']))
                                    {{ number_format($doc['montant'], 2) }} €
                                @else
                                    N/A
                                @endif
                            </td>
                            <td>
                                <span class="badge {{ isset($doc['coherence_ok']) && $doc['coherence_ok'] ? 'badge-success' : 'badge-danger' }}">
                                    {{ isset($doc['coherence_ok']) && $doc['coherence_ok'] ? 'OK' : 'Anomalie' }}
                                </span>
                            </td>
                        </tr>
                        @empty
                        <tr>
                            <td colspan="6" class="text-center py-8 text-gray-500">
                                Aucun document dans le Data Lake
                            </td>
                        </tr>
                        @endforelse
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Fournisseurs -->
        <div class="section-card section-fournisseurs">
            <div class="section-title">
                <span class="section-title-icon">🏭</span>
                Fournisseurs
            </div>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Fournisseur</th>
                            <th>SIREN</th>
                            <th>Total facturé</th>
                            <th>Dernière facture</th>
                            <th>Statut</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>SARL DUPONT</strong><br><small class="text-gray-500">Bâtiment</small></td>
                            <td>123 456 789</td>
                            <td class="montant">12 500 €</td>
                            <td>15/03/2026</td>
                            <td><span class="badge badge-success">À jour</span></td>
                        </tr>
                        <tr>
                            <td><strong>SAS MARTIN</strong><br><small class="text-gray-500">Informatique</small></td>
                            <td>987 654 321</td>
                            <td class="montant">8 750 €</td>
                            <td>14/03/2026</td>
                            <td><span class="badge badge-success">À jour</span></td>
                        </tr>
                        <tr>
                            <td><strong>EURL BERNARD</strong><br><small class="text-gray-500">Conseil</small></td>
                            <td>456 789 123</td>
                            <td class="montant">22 300 €</td>
                            <td>12/03/2026</td>
                            <td><span class="badge badge-warning">En retard</span></td>
                        </tr>
                        <tr>
                            <td><strong>SARL PETIT</strong><br><small class="text-gray-500">Transport</small></td>
                            <td>789 123 456</td>
                            <td class="montant">5 200 €</td>
                            <td>10/03/2026</td>
                            <td><span class="badge badge-success">À jour</span></td>
                        </tr>
                        <tr>
                            <td><strong>SAS DURAND</strong><br><small class="text-gray-500">Formation</small></td>
                            <td>321 654 987</td>
                            <td class="montant">15 800 €</td>
                            <td>08/03/2026</td>
                            <td><span class="badge badge-success">À jour</span></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</body>
<script>
    setTimeout(function() {
        var alert = document.querySelector('.alert-success');
        if (alert) {
            alert.style.transition = 'opacity 1s';
            alert.style.opacity = '0';
            setTimeout(function() {
                alert.style.display = 'none';
            }, 1000);
        }
    }, 3000);
</script>
</html>