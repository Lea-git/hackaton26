<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;

class UsersTableSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    // Dans database/seeders/UsersTableSeeder.php
public function run()
{
    
    // role Commercial pour le user
    \App\Models\User::create([
        'name' => 'Commercial',
        'email' => 'user@docuhack.com',
        'password' => bcrypt('password123'),
        'role' => 'commercial'
    ]);
    
    // Role Conformité pour le Admin
    \App\Models\User::create([
        'name' => 'Conformite',
        'email' => 'admin@docuhack.com',
        'password' => bcrypt('password123'),
        'role' => 'conformite'
    ]);
}
}
