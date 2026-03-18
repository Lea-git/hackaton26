<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DocuHack - Accueil</title>
    @vite(['resources/css/app.css'])
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            margin: 0;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            text-align: center;
            padding: 2rem;
        }
        h1 {
            font-size: 4rem;
            color: white;
            margin-bottom: 0.5rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        .subtitle {
            font-size: 1.5rem;
            color: rgba(255,255,255,0.9);
            margin-bottom: 3rem;
        }
        .buttons {
            display: flex;
            gap: 2rem;
            justify-content: center;
        }
        .btn {
            padding: 1rem 3rem;
            font-size: 1.2rem;
            border: none;
            border-radius: 50px;
            cursor: pointer;
            transition: transform 0.3s, box-shadow 0.3s;
            text-decoration: none;
            font-weight: 600;
        }
        .btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }
        .btn-commercial {
            background: #48bb78;
            color: white;
        }
        .btn-conformite {
            background: #4299e1;
            color: white;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1> DocuHack</h1>
        <p class="subtitle">Traitement automatique de documents administratifs</p>
        
        <div class="buttons">
            <a href="/user/login" class="btn btn-commercial"> Espace Utilisateur</a>
            <a href="/admin/login" class="btn btn-conformite"> Espace Administrateur</a>
        </div>
    </div>
</body>
</html>