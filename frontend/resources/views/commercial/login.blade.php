<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DocuHack - Commercial</title>
    @vite(['resources/sass/app.scss', 'resources/js/app.js'])
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
            min-height: 100vh;
            margin: 0;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-box {
            background: white;
            padding: 3rem;
            border-radius: 10px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            width: 350px;
        }
        h2 {
            margin-bottom: 2rem;
            color: #2d3748;
            text-align: center;
        }
        .form-group {
            margin-bottom: 1.5rem;
        }
        label {
            display: block;
            margin-bottom: 0.5rem;
            color: #4a5568;
            font-weight: 500;
        }
        input {
            width: 100%;
            padding: 0.75rem;
            border: 2px solid #e2e8f0;
            border-radius: 5px;
            font-size: 1rem;
            transition: border-color 0.3s;
            box-sizing: border-box;
        }
        input:focus {
            outline: none;
            border-color: #48bb78;
        }
        button {
            width: 100%;
            padding: 0.75rem;
            background: #48bb78;
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.3s;
        }
        button:hover {
            background: #38a169;
        }
        .back-link {
            text-align: center;
            margin-top: 1.5rem;
        }
        .back-link a {
            color: #718096;
            text-decoration: none;
            font-size: 0.9rem;
        }
        .back-link a:hover {
            color: #48bb78;
        }
    </style>
</head>
<body>
    <div class="login-box">
        <h2> Espace Commercial</h2>
        
        <form method="POST" action="/commercial/login">
            @csrf
            <div class="form-group">
                <label>Email</label>
                <input type="email" name="email" required placeholder="commercial@example.com">
            </div>
            
            <div class="form-group">
                <label>Mot de passe</label>
                <input type="password" name="password" required placeholder="••••••••">
            </div>
            
            <button type="submit">Se connecter</button>
        </form>
        
        <div class="back-link">
            <a href="/">← Retour à l'accueil</a>
        </div>
    </div>
</body>
</html>