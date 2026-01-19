export const SocialProofCardBrand = () => {
  return (
    <section className="bg-primary py-16 md:py-24">
      <div className="mx-auto max-w-container md:px-8">
        <div className="flex flex-col gap-8 bg-brand-section px-6 py-12 md:rounded-2xl md:p-16">
          <p className="text-center text-md font-medium text-tertiary_on-brand md:text-xl">
            Trusted by 4,000+ companies
          </p>
          <div className="flex flex-wrap justify-center gap-x-8 gap-y-4 xl:gap-x-8">
            <img
              alt="Catalog Logo"
              src="https://www.untitledui.com/logos/logotype/white/catalog.svg"
              className="h-9 opacity-85 md:h-12"
            />
            <img
              alt="Pictelai Logo"
              src="https://www.untitledui.com/logos/logotype/white/pictelai.svg"
              className="h-9 opacity-85 md:h-12"
            />
            <img
              alt="Leapyear Logo"
              src="https://www.untitledui.com/logos/logotype/white/leapyear.svg"
              className="h-9 opacity-85 md:h-12"
            />
            <img
              alt="Peregrin Logo"
              src="https://www.untitledui.com/logos/logotype/white/peregrin.svg"
              className="h-9 opacity-85 md:h-12"
            />
            <img
              alt="Easytax Logo"
              src="https://www.untitledui.com/logos/logotype/white/easytax.svg"
              className="h-9 opacity-85 md:h-12"
            />
            <img
              alt="Coreos Logo"
              src="https://www.untitledui.com/logos/logotype/white/coreos.svg"
              className="inline-flex h-9 opacity-85 md:hidden md:h-12"
            />
          </div>
        </div>
      </div>
    </section>
  );
};
