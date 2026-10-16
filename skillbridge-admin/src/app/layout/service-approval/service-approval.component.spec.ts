import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ServiceApprovalComponent } from './service-approval.component';
import { SkillBridgeTestingModule } from '../../../testing/skillbridge-testing.module';

describe('ServiceApprovalComponent', () => {
  let component: ServiceApprovalComponent;
  let fixture: ComponentFixture<ServiceApprovalComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [ServiceApprovalComponent],
      imports: [SkillBridgeTestingModule]
    });
    fixture = TestBed.createComponent(ServiceApprovalComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
