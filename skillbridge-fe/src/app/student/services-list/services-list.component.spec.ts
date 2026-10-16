import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ServicesListComponent } from './services-list.component';
import { SkillBridgeTestingModule } from '../../../testing/skillbridge-testing.module';

describe('ServicesListComponent', () => {
  let component: ServicesListComponent;
  let fixture: ComponentFixture<ServicesListComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [ServicesListComponent],
      imports: [SkillBridgeTestingModule]
    });
    fixture = TestBed.createComponent(ServicesListComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('uses persisted booking status and exposes only valid actions', () => {
    const accepted: any = {
      status: 'ACCEPTED',
      scheduled_start_at: new Date(Date.now() + 86400000).toISOString(),
      reschedule_proposals: []
    };
    expect(component.bookingStatus(accepted)).toBe('ACCEPTED');
    expect(component.canCancel(accepted)).toBeTrue();
    expect(component.canReschedule(accepted)).toBeTrue();

    accepted.reschedule_proposals = [{
      id: 'proposal-1',
      proposal_status: 'PENDING',
      proposed_by_user_id: 'another-user'
    }];
    component.currentUserId = 'student-user';
    expect(component.canReschedule(accepted)).toBeFalse();
    expect(component.canRespondToProposal(accepted)).toBeTrue();
  });
});
