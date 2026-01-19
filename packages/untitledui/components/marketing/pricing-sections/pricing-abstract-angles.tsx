"use client";

import { LayersThree01, LayersTwo01, Zap } from "@untitledui/icons";
import { useState } from "react";
import { Badge } from "@/components/base/badges/badges";
import { Toggle } from "@/components/base/toggle/toggle";
import { BackgroundStripes } from "@/components/marketing/header-section/base-components/background-stripes";
import { PricingTierCardIcon } from "@/components/marketing/pricing-sections/base-components/pricing-tier-card";

export const PricingAbstractAngles = () => {
  const [selectedPlan, setSelectedPlan] = useState("monthly");

  const plans = [
    {
      title: "Basic plan",
      subtitle: selectedPlan === "monthly" ? "$10/mth" : "$9/m",
      description: "Billed annually.",
      features: [
        "Access to all basic features",
        "Basic reporting and analytics",
        "Up to 10 individual users",
        "20 GB individual data",
        "Basic chat and email support",
      ],
      icon: Zap,
    },
    {
      title: "Business plan",
      subtitle: selectedPlan === "monthly" ? "$20/mth" : "$15/m",
      description: "Billed annually.",
      badge: "Popular",
      features: [
        "200+ integrations",
        "Advanced reporting and analytics",
        "Up to 20 individual users",
        "40 GB individual data",
        "Priority chat and email support",
      ],
      icon: LayersTwo01,
    },
    {
      title: "Enterprise plan",
      subtitle: selectedPlan === "monthly" ? "$40/mth" : "$39/m",
      description: "Billed annually.",
      badge: "Popular",
      features: [
        "Advanced custom fields",
        "Audit log and data history",
        "Unlimited individual users",
        "Unlimited individual data",
        "Personalized + priority service",
      ],
      icon: LayersThree01,
    },
  ];

  return (
    <section className="bg-primary">
      <div className="bg-utility-brand-50_alt pt-16 md:pt-24">
        <div className="mx-auto max-w-container px-4 md:px-8">
          <div className="mx-auto flex w-full max-w-3xl flex-col items-center text-center">
            <Badge
              size="lg"
              type="pill-color"
              color="brand"
              className="hidden bg-transparent md:flex"
            >
              Pricing plans
            </Badge>
            <Badge
              size="md"
              type="pill-color"
              color="brand"
              className="bg-transparent md:hidden"
            >
              Pricing plans
            </Badge>

            <h2 className="mt-4 text-display-md font-semibold text-brand-primary md:text-display-lg">
              Plans for all sizes
            </h2>
            <p className="mt-4 text-lg text-brand-secondary md:mt-6 md:text-xl">
              Simple, transparent pricing that grows with you. Try any plan free
              for 30 days.
            </p>
            <div className="mt-8 flex md:mt-12">
              <div className="relative z-10 inline-flex gap-3">
                <Toggle
                  id="annual-pricing"
                  size="md"
                  isSelected={selectedPlan === "annually"}
                  onChange={(value) =>
                    setSelectedPlan(value ? "annually" : "monthly")
                  }
                />

                <label
                  htmlFor="annual-pricing"
                  className="text-md font-medium text-brand-primary select-none"
                >
                  Annual pricing{" "}
                  <span className="text-brand-secondary">(save 20%)</span>
                </label>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="relative py-16 md:py-24">
        <BackgroundStripes />
        <div className="relative mx-auto max-w-container px-4 md:px-8">
          <div className="grid w-full grid-cols-1 gap-4 md:grid-cols-2 md:gap-8 xl:grid-cols-3">
            {plans.map((plan) => (
              <PricingTierCardIcon
                key={plan.title}
                {...plan}
                iconTheme="modern"
                iconColor="gray"
              />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};
