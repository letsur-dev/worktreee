export const ContactCenteredMap = () => {
  return (
    <section className="bg-primary py-16 md:py-24">
      <div className="mx-auto max-w-container px-4 md:px-8">
        <div className="flex w-full max-w-3xl flex-col lg:mx-auto lg:items-center lg:text-center">
          <span className="text-sm font-semibold text-brand-secondary md:text-md">
            Our locations
          </span>
          <h2 className="mt-3 text-display-sm font-semibold text-primary md:text-display-md">
            Visit our stores
          </h2>
          <p className="mt-4 text-lg text-tertiary md:mt-5 md:text-xl">
            Say hello to our friendly team at one of these locations.
          </p>
        </div>

        <div className="mt-12 grid grid-cols-1 items-start md:mt-16 md:grid-cols-[1fr_1fr] lg:grid-cols-[1fr_1fr_1fr] lg:gap-16">
          <ul className="grid grid-cols-1 gap-y-6 lg:gap-y-12">
            {[
              {
                title: "Melbourne",
                subtitle: "100 Flinders Street\nMelbourne VIC 3000 AU",
              },
              {
                title: "Sydney",
                subtitle: "100 George Street\nSydney NSW 2000 AU",
              },
              {
                title: "Byron Bay",
                subtitle: "100 Jonson Street\nByron Bay NSW 2481 AU",
              },
            ].map((item) => (
              <li
                key={item.title}
                className="flex max-w-sm flex-col lg:text-center"
              >
                <h3 className="text-lg font-semibold text-primary">
                  {item.title}
                </h3>
                <p className="mt-1 text-md whitespace-pre text-tertiary">
                  {item.subtitle}
                </p>
              </li>
            ))}
          </ul>

          <ul className="mt-6 grid grid-cols-1 gap-y-6 sm:mt-0 lg:gap-y-12">
            {[
              {
                title: "London",
                subtitle: "100 Oxford Street\nLondon W1D 1LL UK",
              },
              {
                title: "San Francisco",
                subtitle: "100 Market Street\nSan Francisco, CA 94105 USA",
              },
              {
                title: "Sweden",
                subtitle: "Drottninggatan 100\n111 60 Stockholm SE",
              },
            ].map((item) => (
              <li
                key={item.title}
                className="flex max-w-sm flex-col lg:text-center"
              >
                <h3 className="text-lg font-semibold text-primary">
                  {item.title}
                </h3>
                <p className="mt-1 text-md whitespace-pre text-tertiary">
                  {item.subtitle}
                </p>
              </li>
            ))}
          </ul>

          <iframe
            title="Our address"
            src="https://snazzymaps.com/embed/451894"
            className="mt-12 h-60 w-full border-none md:col-span-2 lg:col-auto lg:col-start-2 lg:row-start-1 lg:mt-0 lg:h-full lg:w-110 xl:w-140"
            data-chromatic="ignore"
          />
        </div>
      </div>
    </section>
  );
};
