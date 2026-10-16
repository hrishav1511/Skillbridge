import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ApprovalCardComponent } from './approval-card.component';
import { SkillBridgeTestingModule } from '../../../../testing/skillbridge-testing.module';

describe('ApprovalCardComponent', () => {
  let component: ApprovalCardComponent;
  let fixture: ComponentFixture<ApprovalCardComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [ApprovalCardComponent],
      imports: [SkillBridgeTestingModule]
    });
    fixture = TestBed.createComponent(ApprovalCardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
