import { ComponentFixture, TestBed } from '@angular/core/testing';

import { UserActionComponent } from './user-action.component';
import { SkillBridgeTestingModule } from '../../../../testing/skillbridge-testing.module';

describe('UserActionComponent', () => {
  let component: UserActionComponent;
  let fixture: ComponentFixture<UserActionComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [UserActionComponent],
      imports: [SkillBridgeTestingModule]
    });
    fixture = TestBed.createComponent(UserActionComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
