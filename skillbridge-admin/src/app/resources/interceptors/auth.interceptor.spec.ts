import { TestBed } from '@angular/core/testing';

import { AuthInterceptor } from './auth.interceptor';
import { SkillBridgeTestingModule } from '../../../testing/skillbridge-testing.module';

describe('AuthInterceptor', () => {
  beforeEach(() => TestBed.configureTestingModule({
    imports: [SkillBridgeTestingModule],
    providers: [
      AuthInterceptor
      ]
  }));

  it('should be created', () => {
    const interceptor: AuthInterceptor = TestBed.inject(AuthInterceptor);
    expect(interceptor).toBeTruthy();
  });
});
