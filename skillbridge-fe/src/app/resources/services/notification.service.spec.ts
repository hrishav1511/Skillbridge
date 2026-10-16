import { TestBed } from '@angular/core/testing';

import { NotificationService } from './notification.service';
import { SkillBridgeTestingModule } from '../../../testing/skillbridge-testing.module';

describe('NotificationService', () => {
  let service: NotificationService;

  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [SkillBridgeTestingModule] });
    service = TestBed.inject(NotificationService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
