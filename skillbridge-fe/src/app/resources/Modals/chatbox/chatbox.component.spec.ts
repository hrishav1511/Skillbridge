import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ChatboxComponent } from './chatbox.component';
import { SkillBridgeTestingModule } from '../../../../testing/skillbridge-testing.module';
import { DIALOG_DATA } from '@angular/cdk/dialog';

describe('ChatboxComponent', () => {
  let component: ChatboxComponent;
  let fixture: ComponentFixture<ChatboxComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [ChatboxComponent],
      imports: [SkillBridgeTestingModule],
      providers: [{ provide: DIALOG_DATA, useValue: { tutor: { user: { full_name: 'Test Tutor' } }, chat_id: 'room-id' } }]
    });
    fixture = TestBed.createComponent(ChatboxComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
