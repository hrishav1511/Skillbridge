import { Injectable } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivate, Router, UrlTree } from '@angular/router';

@Injectable({ providedIn: 'root' })
export class RoleGuard implements CanActivate {
  constructor(private router: Router) {}

  canActivate(route: ActivatedRouteSnapshot): boolean | UrlTree {
    const role = (localStorage.getItem('user_ROLE') || '').toUpperCase();
    const token = localStorage.getItem('access_token');
    if (route.data['allowGuest'] && role === 'GUEST') {
      return true;
    }
    const allowedRoles = (route.data['roles'] || []) as string[];
    if (token && (!allowedRoles.length || allowedRoles.includes(role))) {
      return true;
    }
    return this.router.createUrlTree(['/auth/login']);
  }
}
