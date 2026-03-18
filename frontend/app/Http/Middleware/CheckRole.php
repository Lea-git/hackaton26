<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

class CheckRole
{
    public function handle(Request $request, Closure $next, $role)
    {
        if (!Auth::check()) {  
            abort(403, 'Non authentifié');
        }

        if (Auth::user()->role !== $role) {
            abort(403, 'Accès non autorisé');
        }

        return $next($request);
    }
}