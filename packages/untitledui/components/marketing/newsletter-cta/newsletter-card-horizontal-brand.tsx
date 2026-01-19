"use client";

import { Button } from "@/components/base/buttons/button";
import { Form } from "@/components/base/form/form";
import { Input } from "@/components/base/input/input";

export const NewsletterCardHorizontalBrand = () => {
  return (
    <section className="bg-primary py-16 md:py-24">
      <div className="mx-auto max-w-container px-4 md:px-8">
        <div className="flex flex-col justify-between gap-x-16 gap-y-8 rounded-2xl bg-brand-section px-6 py-10 lg:flex-row lg:p-16">
          <div className="flex max-w-3xl flex-col">
            <h2 className="text-display-sm font-semibold text-primary_on-brand md:text-display-md">
              Join 2,000+ subscribers
            </h2>
            <p className="mt-4 text-lg text-tertiary_on-brand md:mt-5 lg:text-xl">
              Stay in the loop with everything you need to know.
            </p>
          </div>
          <Form
            onSubmit={(e) => {
              e.preventDefault();
              const data = Object.fromEntries(new FormData(e.currentTarget));
              console.log("Form data:", data);
            }}
            className="flex w-full flex-col gap-4 md:max-w-120 md:flex-row"
          >
            <Input
              isRequired
              size="md"
              name="email"
              type="email"
              placeholder="Enter your email"
              inputClassName="border-none"
              wrapperClassName="flex-1 py-0.5 md:max-w-[345px]"
              hint={
                <span className="text-tertiary_on-brand">
                  <span className="md:hidden">Read about our</span>
                  <span className="max-md:hidden">
                    We care about your data in our
                  </span>{" "}
                  <a
                    href="#"
                    className="rounded-xs underline underline-offset-3 outline-focus-ring focus-visible:outline-2 focus-visible:outline-offset-2"
                  >
                    privacy policy
                  </a>
                  .
                </span>
              }
            />
            <Button type="submit" size="xl">
              Subscribe
            </Button>
          </Form>
        </div>
      </div>
    </section>
  );
};
