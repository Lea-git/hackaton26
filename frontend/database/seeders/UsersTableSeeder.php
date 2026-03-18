<?php

namespace Database\Seeders;

use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;

class UsersTableSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    // Dans database/seeders/UsersTableSeeder.php
public function run()
{
    // Admin
    \App\Models\User::create([
        'name' => 'Admin',
        'email' => 'admin@docuhack.com',
        'password' => bcrypt('admin123'),
        'role' => 'admin'
    ]);
    
    // Commercial
    \App\Models\User::create([
        'name' => 'Commercial',
        'email' => 'commercial@docuhack.com',
        'password' => bcrypt('password123'),
        'role' => 'commercial'
    ]);
    
    // Conformité
    \App\Models\User::create([
        'name' => 'Conformite',
        'email' => 'conformite@docuhack.com',
        'password' => bcrypt('password123'),
        'role' => 'conformite'
    ]);
}
}
