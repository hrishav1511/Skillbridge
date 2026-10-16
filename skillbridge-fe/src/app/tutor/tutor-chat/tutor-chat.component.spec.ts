import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TutorChatComponent } from './tutor-chat.component';
import { SkillBridgeTestingModule } from '../../../testing/skillbridge-testing.module';

describe('TutorChatComponent', () => {
  let component: TutorChatComponent;
  let fixture: ComponentFixture<TutorChatComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [TutorChatComponent],
      imports: [SkillBridgeTestingModule]
    });
    fixture = TestBed.createComponent(TutorChatComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
