import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FormControl } from '@angular/forms';

import { SignInComponent, passwordComplexityValidator } from './sign-in.component';
import { SkillBridgeTestingModule } from '../../../testing/skillbridge-testing.module';

describe('SignInComponent', () => {
  let component: SignInComponent;
  let fixture: ComponentFixture<SignInComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [SignInComponent],
      imports: [SkillBridgeTestingModule]
    });
    fixture = TestBed.createComponent(SignInComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should reject passwords that do not include uppercase, lowercase, number, and special character', () => {
    const control = new FormControl('password123');

    expect(passwordComplexityValidator(control)).toEqual({ weakPassword: true });
  });
});
