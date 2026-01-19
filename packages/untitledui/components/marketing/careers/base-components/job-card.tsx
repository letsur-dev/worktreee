"use client";

import {
  ArrowUpRight,
  Clock,
  CurrencyDollarCircle,
  MarkerPin02,
} from "@untitledui/icons";
import type { BadgeColors } from "@/components/base/badges/badge-types";
import { BadgeWithDot, BadgeWithFlag } from "@/components/base/badges/badges";
import { Button } from "@/components/base/buttons/button";

export interface JobCardSimpleProps {
  title: string;
  description: string;
  href: string;
  location: string;
  type: string;
  badgeText?: string;
  badgeColor: BadgeColors;
}

export const JobCardSimple = (props: JobCardSimpleProps) => {
  return (
    <a
      href={props.href}
      className="relative flex flex-col rounded-xs pt-6 outline-focus-ring focus-visible:outline-2 focus-visible:outline-offset-4"
    >
      <div className="absolute top-0 h-px w-full border-t border-secondary"></div>
      <div className="flex flex-col items-start gap-2 md:flex-row md:items-center">
        <h3 className="text-md font-semibold text-primary">{props.title}</h3>
        <BadgeWithDot color={props.badgeColor} size="md" type="pill-color">
          {props.badgeText}
        </BadgeWithDot>
      </div>
      <p className="mt-2 text-md text-tertiary">{props.description}</p>
      <div className="mt-5 flex gap-4">
        <div className="flex items-center gap-1.5">
          <MarkerPin02 size={20} className="text-fg-quaternary" />
          <span className="text-sm font-medium text-tertiary">
            {props.location}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <Clock size={20} className="text-fg-quaternary" />
          <span className="text-sm font-medium text-tertiary">
            {props.type}
          </span>
        </div>
      </div>
    </a>
  );
};

export interface JobCard01Props extends JobCardSimpleProps {
  department: string;
}

export const JobCard01 = (props: JobCard01Props) => {
  return (
    <a
      href={props.href}
      className="flex flex-col rounded-2xl bg-primary p-6 pb-6 ring-1 ring-secondary outline-focus-ring ring-inset focus-visible:outline-2 focus-visible:outline-offset-2 md:pb-7"
    >
      <div className="flex items-center justify-between py-0.5 md:py-0">
        <span className="text-sm font-semibold text-brand-secondary">
          {props.department}
        </span>
        <Button
          color="link-color"
          size="sm"
          className="hidden md:flex"
          iconTrailing={ArrowUpRight}
        >
          View job
        </Button>
        <div className="flex md:hidden">
          <BadgeWithDot color={props.badgeColor} size="md">
            {props.badgeText}
          </BadgeWithDot>
        </div>
      </div>
      <div className="flex items-center gap-2 md:mt-0.5">
        <h3 className="text-md font-semibold text-primary">{props.title}</h3>
        <div className="hidden md:flex">
          <BadgeWithDot color={props.badgeColor} size="md">
            {props.badgeText}
          </BadgeWithDot>
        </div>
      </div>
      <p className="mt-2 text-md text-tertiary">{props.description}</p>
      <div className="mt-5 flex gap-4">
        <div className="flex items-center gap-1.5">
          <MarkerPin02 size={20} className="text-fg-quaternary" />
          <span className="text-sm font-medium text-tertiary">
            {props.location}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <Clock size={20} className="text-fg-quaternary" />
          <span className="text-sm font-medium text-tertiary">
            {props.type}
          </span>
        </div>
      </div>
    </a>
  );
};

export interface JobCard02Props extends Omit<JobCardSimpleProps, "location"> {
  salary: string;
  location: { city: string; country: string; countryCode: string };
}

export const JobCard02 = (props: JobCard02Props) => {
  return (
    <a
      href={props.href}
      className="flex flex-col rounded-2xl bg-primary p-6 ring-1 ring-secondary outline-focus-ring ring-inset focus-visible:outline-2 focus-visible:outline-offset-2"
    >
      <div className="flex flex-col items-start gap-2 md:flex-row">
        <h3 className="text-md font-semibold text-primary">{props.title}</h3>

        <div className="flex flex-1 gap-2 md:flex-row-reverse md:justify-between">
          <BadgeWithFlag flag="AU" color="gray" size="md" type="modern">
            <span>
              {props.location.city},{" "}
              <span className="hidden md:inline-flex">
                {props.location.country}
              </span>
              <span className="inline-flex md:hidden">
                {props.location.countryCode}
              </span>
            </span>
          </BadgeWithFlag>

          <BadgeWithDot color={props.badgeColor} size="md" type="modern">
            {props.badgeText}
          </BadgeWithDot>
        </div>
      </div>

      <p className="mt-2 text-md text-tertiary">{props.description}</p>

      <div className="mt-5 flex gap-4">
        <div className="flex items-center gap-1.5">
          <Clock size={20} className="text-fg-quaternary" />
          <span className="text-sm font-medium text-tertiary">
            {props.type}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <CurrencyDollarCircle size={20} className="text-fg-quaternary" />
          <span className="text-sm font-medium text-tertiary">
            {props.salary}
          </span>
        </div>
      </div>
    </a>
  );
};
