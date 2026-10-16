import { ComponentFixture, TestBed } from '@angular/core/testing';
import { AdminChatComponent } from './admin-chat.component';
import { SkillBridgeTestingModule } from '../../../testing/skillbridge-testing.module';

describe('AdminChatComponent', () => {
  let fixture: ComponentFixture<AdminChatComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [AdminChatComponent],
      imports: [SkillBridgeTestingModule]
    });
    fixture = TestBed.createComponent(AdminChatComponent);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });
});
