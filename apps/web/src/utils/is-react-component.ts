import type React from "react";

type ReactComponent = React.FC<unknown> | React.ComponentClass<unknown, unknown>;

export const isFunctionComponent = (
  component: unknown,
): component is React.FC<unknown> => {
  return typeof component === "function";
};

export const isClassComponent = (
  component: unknown,
): component is React.ComponentClass<unknown, unknown> => {
  return (
    typeof component === "function" &&
    !!(component as React.ComponentClass).prototype &&
    (!!((component as React.ComponentClass).prototype as { isReactComponent?: boolean }).isReactComponent ||
      !!((component as React.ComponentClass).prototype as { render?: () => unknown }).render)
  );
};

export const isForwardRefComponent = (
  component: unknown,
): component is React.ForwardRefExoticComponent<unknown> => {
  return (
    typeof component === "object" &&
    component !== null &&
    (component as { $$typeof?: symbol }).$$typeof?.toString() === "Symbol(react.forward_ref)"
  );
};

export const isReactComponent = (
  component: unknown,
): component is ReactComponent => {
  return (
    isFunctionComponent(component) ||
    isForwardRefComponent(component) ||
    isClassComponent(component)
  );
};
