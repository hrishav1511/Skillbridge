import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SidepanelComponent } from './sidepanel.component';
import { SkillBridgeTestingModule } from '../../../testing/skillbridge-testing.module';
import { routes } from '../layout-routing.module';

describe('SidepanelComponent', () => {
  let component: SidepanelComponent;
  let fixture: ComponentFixture<SidepanelComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [SidepanelComponent],
      imports: [SkillBridgeTestingModule]
    });
    fixture = TestBed.createComponent(SidepanelComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  /*
   * Every nav item must point at a route that actually exists.
   *
   * The Tutors and Services links shipped pointing at panel/tutors and
   * panel/services while those routes were missing from the routing module,
   * so clicking them did nothing at all. This compares the two lists so a
   * dead link fails here instead of in the browser.
   */
  it('links only to routes the layout actually declares', () => {
    const declared = new Set(
      (routes[0].children || []).map((route) => route.path)
    );

    const links: string[] = Array.from(
      fixture.nativeElement.querySelectorAll('a.nav__item')
    )
      .map((anchor) => (anchor as HTMLElement).getAttribute('ng-reflect-router-link'))
      .filter((link): link is string => !!link)
      .map((link) => link.replace(/^\.?\//, ''));

    const dead = links.filter((link) => !declared.has(link));
    expect(dead).withContext(`nav links with no route: ${dead.join(', ')}`).toEqual([]);
  });
});
