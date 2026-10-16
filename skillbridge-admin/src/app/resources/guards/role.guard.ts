import { Injectable } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivate, Router, UrlTree } from '@angular/router';

@Injectable({ providedIn: 'root' })
export class RoleGuard implements CanActivate {
  constructor(private router: Router) {}

  canActivate(route: ActivatedRouteSnapshot): boolean | UrlTree {
    const token = localStorage.getItem('access_token');
    const role = (localStorage.getItem('user_ROLE') || '').toUpperCase();
    const allowedRoles = (route.data['roles'] || ['ADMIN', 'SUPER_ADMIN']) as string[];
    return token && allowedRoles.includes(role)
      ? true
      : this.router.createUrlTree(['/auth/login']);
  }
}
