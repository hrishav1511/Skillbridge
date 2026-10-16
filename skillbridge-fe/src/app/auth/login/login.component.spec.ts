import { ComponentFixture, TestBed } from '@angular/core/testing';

import { LoginComponent } from './login.component';
import { SkillBridgeTestingModule } from '../../../testing/skillbridge-testing.module';
import { Router } from '@angular/router';

describe('LoginComponent', () => {
  let component: LoginComponent;
  let fixture: ComponentFixture<LoginComponent>;
  let router: Router;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [LoginComponent],
      imports: [SkillBridgeTestingModule]
    });
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    fixture = TestBed.createComponent(LoginComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should store dummy session data for guest access', () => {
    localStorage.clear();

    component.continueAsGuest();

    expect(localStorage.getItem('userData')).toContain('Guest');
    expect(localStorage.getItem('user_id')).toBe('"guest-user"');
    expect(localStorage.getItem('access_token')).toBeNull();
    expect(localStorage.getItem('refresh_token')).toBeNull();
    expect(localStorage.getItem('token_type')).toBeNull();
    expect(localStorage.getItem('token_expires_in')).toBeNull();
    expect(localStorage.getItem('user_ROLE')).toBe('GUEST');
    expect(router.navigate).toHaveBeenCalledWith(['/student/dashboard']);
  });
});
