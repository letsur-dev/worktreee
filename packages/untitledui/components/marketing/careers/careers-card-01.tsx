"use client";

import { useState } from "react";
import { TabList, Tabs } from "@/components/application/tabs/tabs";
import { NativeSelect } from "@/components/base/select/select-native";
import {
  JobCard01,
  type JobCard01Props,
} from "@/components/marketing/careers/base-components/job-card";

const jobs: JobCard01Props[] = [
  {
    title: "Product Designer",
    department: "Design",
    description:
      "We're looking for a mid-level product designer to join our team.",
    href: "#",
    badgeColor: "blue",
    badgeText: "Design",
    location: "Remote",
    type: "Full-time",
  },
  {
    title: "Engineering Manager",
    department: "Software Development",
    description:
      "We're looking for a mid-level product designer to join our team.",
    href: "#",
    badgeColor: "pink",
    badgeText: "Software",
    location: "Remote",
    type: "Full-time",
  },
  {
    title: "Customer Success Manager",
    department: "Customer Success",
    description:
      "We're looking for a mid-level product designer to join our team.",
    href: "#",
    badgeColor: "success",
    badgeText: "CX",
    location: "Remote",
    type: "Full-time",
  },
  {
    title: "Account Executive",
    department: "Sales",
    description:
      "We're looking for a mid-level product designer to join our team.",
    href: "#",
    badgeColor: "indigo",
    badgeText: "Sales",
    location: "Remote",
    type: "Full-time",
  },
  {
    title: "SEO Marketing Manager",
    department: "Marketing",
    description:
      "We're looking for a mid-level product designer to join our team.",
    href: "#",
    badgeColor: "orange",
    badgeText: "Marketing",
    location: "Remote",
    type: "Full-time",
  },
];

const departments = [
  {
    id: "all",
    label: "View all",
  },
  {
    id: "design",
    label: "Design",
  },
  {
    id: "softwareEngineering",
    label: "Software Engineering",
  },
  {
    id: "customerSuccess",
    label: "Customer Success",
  },
  {
    id: "sales",
    label: "Sales",
  },
  {
    id: "marketing",
    label: "Marketing",
  },
];

export const CareersCard01 = () => {
  const [selectedTab, setSelectedTab] = useState("all");

  return (
    <section className="bg-primary py-16 md:py-24">
      <div className="mx-auto max-w-container px-4 md:px-8">
        <div className="mx-auto flex w-full max-w-3xl flex-col items-center text-center">
          <h2 className="text-display-sm font-semibold text-primary md:text-display-md">
            Open positions
          </h2>
          <p className="mt-4 text-lg text-tertiary md:mt-5 md:text-xl">
            We're a 100% remote team spread all across the world. Join us!
          </p>
        </div>

        <div className="mt-12 w-full md:mx-auto md:mt-16 md:w-max">
          <NativeSelect
            aria-label="Departments"
            className="md:hidden"
            value={departments.find(({ id }) => id === selectedTab)?.id ?? ""}
            onChange={(event) => setSelectedTab(event.target.value)}
            options={departments.map((tab) => ({
              label: tab.label,
              value: tab.id,
            }))}
          />
          <Tabs className="max-md:hidden">
            <TabList size="md" type="button-border" items={departments} />
          </Tabs>
        </div>

        <div className="mx-auto mt-8 max-w-3xl md:mt-16">
          <ul className="flex flex-col gap-4 md:gap-6">
            {jobs.map((job) => (
              <li key={job.title}>
                <JobCard01 {...job} />
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
};
