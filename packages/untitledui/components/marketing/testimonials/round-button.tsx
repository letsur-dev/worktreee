"use client";

import type { ComponentPropsWithRef, FC } from "react";
import { Button } from "@/components/base/buttons/button";
import { cx } from "@/utils/cx";
import { isReactComponent } from "@/utils/is-react-component";

interface RoundButtonProps extends ComponentPropsWithRef<"button"> {
  icon?: FC<{ className?: string }>;
}

export const RoundButton = ({ icon: Icon, ...props }: RoundButtonProps) => {
  return (
    <Button
      {...props}
      color="link-gray"
      className={cx(
        "group flex size-12 items-center justify-center rounded-full bg-primary ring-1 ring-secondary backdrop-blur transition duration-100 ease-linear ring-inset hover:bg-secondary md:size-14",
        props.className,
      )}
    >
      {props.children ??
        (isReactComponent(Icon) ? (
          <Icon className="size-5 text-fg-quaternary transition-inherit-all group-hover:text-fg-quaternary_hover md:size-6" />
        ) : null)}
    </Button>
  );
};
