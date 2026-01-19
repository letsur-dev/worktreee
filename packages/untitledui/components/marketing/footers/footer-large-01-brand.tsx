import { Button } from "@/components/base/buttons/button";
import { UntitledLogo } from "@/components/foundations/logo/untitledui-logo";

const footerNavList = [
  {
    label: "Product",
    items: [
      {
        label: "Overview",
        href: "#",
      },
      {
        label: "Features",
        href: "#",
      },
      {
        label: "Solutions",
        href: "#",
        badge: (
          <span className="ml-1 rounded-md bg-white/10 px-1.5 py-0.5 text-xs font-medium text-white ring-1 ring-white/30 ring-inset">
            New
          </span>
        ),
      },
      {
        label: "Tutorials",
        href: "#",
      },
      {
        label: "Pricing",
        href: "#",
      },
      {
        label: "Releases",
        href: "#",
      },
    ],
  },
  {
    label: "Company",
    items: [
      {
        label: "About us",
        href: "#",
      },
      {
        label: "Careers",
        href: "#",
      },
      {
        label: "Press",
        href: "#",
      },
      {
        label: "News",
        href: "#",
      },
      {
        label: "Media kit",
        href: "#",
      },
      {
        label: "Contact",
        href: "#",
      },
    ],
  },
  {
    label: "Resources",
    items: [
      {
        label: "Blog",
        href: "#",
      },
      {
        label: "Newsletter",
        href: "#",
      },
      {
        label: "Events",
        href: "#",
      },
      {
        label: "Help centre",
        href: "#",
      },
      {
        label: "Tutorials",
        href: "#",
      },
      {
        label: "Support",
        href: "#",
      },
    ],
  },
  {
    label: "Use cases",
    items: [
      {
        label: "Startups",
        href: "#",
      },
      {
        label: "Enterprise",
        href: "#",
      },
      {
        label: "Government",
        href: "#",
      },
      {
        label: "SaaS centre",
        href: "#",
      },
      {
        label: "Marketplaces",
        href: "#",
      },
      {
        label: "Ecommerce",
        href: "#",
      },
    ],
  },
  {
    label: "Social",
    items: [
      {
        label: "Twitter",
        href: "#",
      },
      {
        label: "LinkedIn",
        href: "#",
      },
      {
        label: "Facebook",
        href: "#",
      },
      {
        label: "GitHub",
        href: "#",
      },
      {
        label: "AngelList",
        href: "#",
      },
      {
        label: "Dribbble",
        href: "#",
      },
    ],
  },
  {
    label: "Legal",
    items: [
      {
        label: "Terms",
        href: "#",
      },
      {
        label: "Privacy",
        href: "#",
      },
      {
        label: "Cookies",
        href: "#",
      },
      {
        label: "Licenses",
        href: "#",
      },
      {
        label: "Settings",
        href: "#",
      },
      {
        label: "Contact",
        href: "#",
      },
    ],
  },
];

export const FooterLarge01Brand = () => {
  return (
    <footer className="bg-brand-section py-12 md:pt-16">
      <div className="mx-auto max-w-container px-4 md:px-8">
        <nav>
          <ul className="grid grid-cols-2 gap-8 md:grid-cols-3 lg:grid-cols-6">
            {footerNavList.map((category) => (
              <li key={category.label}>
                <h4 className="text-sm font-semibold text-quaternary_on-brand">
                  {category.label}
                </h4>
                <ul className="mt-4 flex flex-col gap-3">
                  {category.items.map((item) => (
                    <li key={item.label}>
                      <Button
                        className="gap-1 text-footer-button-fg hover:text-footer-button-fg_hover"
                        color="link-color"
                        size="lg"
                        href={item.href}
                        iconTrailing={item.badge}
                      >
                        {item.label}
                      </Button>
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </nav>
        <div className="mt-12 flex flex-col justify-between gap-6 border-t border-brand_alt pt-8 md:mt-16 md:flex-row md:items-center">
          <UntitledLogo className="dark-mode" />
          <p className="text-md text-quaternary_on-brand">
            © 2077 Untitled UI. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
};
