import { ComponentFixture, TestBed } from '@angular/core/testing';

import { RejectCardComponent } from './reject-card.component';
import { SkillBridgeTestingModule } from '../../../../testing/skillbridge-testing.module';

describe('RejectCardComponent', () => {
  let component: RejectCardComponent;
  let fixture: ComponentFixture<RejectCardComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [RejectCardComponent],
      imports: [SkillBridgeTestingModule]
    });
    fixture = TestBed.createComponent(RejectCardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
