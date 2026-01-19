"use client";

import { Link01 } from "@untitledui/icons";
import { BadgeGroup } from "@/components/base/badges/badge-groups";
import { Badge } from "@/components/base/badges/badges";

export const ContentAlternative01 = () => {
  return (
    <div className="bg-primary">
      <div className="mx-auto grid max-w-container grid-cols-1 gap-16 bg-primary px-4 pb-16 md:px-8 md:pb-24 lg:grid-cols-2 lg:gap-16 lg:pt-16">
        <img
          className="hidden h-160 object-cover lg:block"
          src="https://www.untitledui.com/marketing/podcast-girl-3.webp"
          alt="Podcast girl"
        />

        <div className="flex flex-col justify-center gap-16 pt-16 lg:gap-32 lg:pt-32">
          <div className="flex flex-col items-start">
            <BadgeGroup
              size="md"
              addonText="12 Jan 2025"
              color="brand"
              theme="modern"
              className="pr-3"
              iconTrailing={null}
            >
              Customer Success
            </BadgeGroup>
            <h1 className="mt-4 text-display-md font-semibold text-primary md:text-display-lg">
              Podcast: Creating a better CX Community
            </h1>
            <p className="mt-4 text-lg text-tertiary md:mt-8 md:text-xl">
              Starting a community doesn't need to be complicated, but how do
              you get started? Learn how with the best.
            </p>
            <div className="mt-8 flex items-center gap-3 md:mt-12">
              <img
                src="https://www.untitledui.com/images/avatars/orlando-diggs?fm=webp&q=80"
                className="size-12 rounded-full object-cover"
                alt="Orlando Diggs"
              />
              <div>
                <p className="text-md font-semibold text-primary">
                  Orlando Diggs
                </p>
                <p className="text-md text-tertiary">CX Lead, Layers</p>
              </div>
            </div>

            <img
              className="mt-16 h-60 w-full object-cover md:h-110 lg:hidden"
              src="https://images.unsplash.com/photo-1489769002049-ccd828976a6c?ixid=MnwzOTA3NTV8MHwxfHNlYXJjaHw3fHxsaWdodCUyMHdhbGwlMjB3aXRoJTIwcGljdHVyZXN8ZW58MHx8fHwxNjcxNjk2OTIx&ixlib=rb-4.0.3"
              alt="Light wall with pictures"
            />
          </div>

          <div className="mx-auto max-w-prose lg:max-w-180">
            <div className="prose-centered-quote mx-auto prose md:prose-lg">
              <p className="lead">
                Lorem ipsum dolor sit amet, consectetur adipiscing elit. Donec
                ullamcorper mattis lorem non. Ultrices praesent amet ipsum justo
                massa. Eu dolor aliquet risus gravida nunc at feugiat consequat
                purus. Non massa enim vitae duis mattis. Vel in ultricies vel
                fringilla.
              </p>
              <hr />
              <h2>Introduction</h2>
              <p>
                Mi tincidunt elit, id quisque ligula ac diam, amet. Vel etiam
                suspendisse morbi eleifend faucibus eget vestibulum felis.
                Dictum quis montes, sit sit. Tellus aliquam enim urna, etiam.
                Mauris posuere vulputate arcu amet, vitae nisi, tellus
                tincidunt. At feugiat sapien varius id.
              </p>
              <p>
                Eget quis mi enim, leo lacinia pharetra, semper. Eget in
                volutpat mollis at volutpat lectus velit, sed auctor. Porttitor
                fames arcu quis fusce augue enim. Quis at habitant diam at.
                Suscipit tristique risus, at donec. In turpis vel et quam
                imperdiet. Ipsum molestie aliquet sodales id est ac volutpat.
              </p>
              <figure>
                <img
                  alt="Man sitting with a laptop on his lap"
                  className="h-60 md:h-96"
                  src="https://images.pexels.com/photos/4939620/pexels-photo-4939620.jpeg?cs=srgb&dl=pexels-vlada-karpovich-4939620.jpg&fm=jpg&w=1280&h=853"
                />
                <figcaption>
                  <Link01 className="size-4 text-utility-gray-400" />
                  <span>
                    Image courtesy of Vlada Karpovich via{" "}
                    <a
                      href="https://www.pexels.com/photo/man-sitting-with-a-laptop-on-his-lap-4939620/"
                      className="rounded-xs outline-focus-ring focus-visible:outline-2 focus-visible:outline-offset-2"
                    >
                      Pexels
                    </a>
                  </span>
                </figcaption>
              </figure>
              <p>
                Ipsum sit mattis nulla quam nulla. Gravida id gravida ac enim
                mauris id. Non pellentesque congue eget consectetur turpis.
                Sapien, dictum molestie sem tempor. Diam elit, orci, tincidunt
                aenean tempus. Quis velit eget ut tortor tellus. Sed vel, congue
                felis elit erat nam nibh orci.
              </p>

              <figure>
                <blockquote>
                  <p>
                    In a world older and more complete than ours they move
                    finished and complete, gifted with extensions of the senses
                    we have lost or never attained, living by voices we shall
                    never hear.
                  </p>
                </blockquote>
                <figcaption className="not-prose mt-6 inline-flex flex-col items-center md:mt-8">
                  <img
                    alt="Olivia Rhye"
                    src="https://www.untitledui.com/images/avatars/olivia-rhye?fm=webp&q=80"
                    className="size-10 rounded-full object-cover"
                  />
                  <p className="mt-3 text-md font-semibold text-primary">
                    Olivia Rhye
                  </p>
                  <cite className="mt-0.5 text-md text-tertiary not-italic">
                    Product Designer
                  </cite>
                </figcaption>
              </figure>
              <p>
                Dolor enim eu tortor urna sed duis nulla. Aliquam vestibulum,
                nulla odio nisl vitae. In aliquet pellentesque aenean hac
                vestibulum turpis mi bibendum diam. Tempor integer aliquam in
                vitae malesuada fringilla.
              </p>
              <p>
                Elit nisi in eleifend sed nisi. Pulvinar at orci, proin
                imperdiet commodo consectetur convallis risus. Sed condimentum
                enim dignissim adipiscing faucibus consequat, urna. Viverra
                purus et erat auctor aliquam. Risus, volutpat vulputate posuere
                purus sit congue convallis aliquet. Arcu id augue ut feugiat
                donec porttitor neque. Mauris, neque ultricies eu vestibulum,
                bibendum quam lorem id. Dolor lacus, eget nunc lectus in tellus,
                pharetra, porttitor.
              </p>
              <p>
                Ipsum sit mattis nulla quam nulla. Gravida id gravida ac enim
                mauris id. Non pellentesque congue eget consectetur turpis.
                Sapien, dictum molestie sem tempor. Diam elit, orci, tincidunt
                aenean tempus. Quis velit eget ut tortor tellus. Sed vel, congue
                felis elit erat nam nibh orci.
              </p>
              <h3>Software and tools</h3>
              <p>
                Mi tincidunt elit, id quisque ligula ac diam, amet. Vel etiam
                suspendisse morbi eleifend faucibus eget vestibulum felis.
                Dictum quis montes, sit sit. Tellus aliquam enim urna, etiam.
                Mauris posuere vulputate arcu amet, vitae nisi, tellus
                tincidunt. At feugiat sapien varius id.
              </p>
              <p>
                Eget quis mi enim, leo lacinia pharetra, semper. Eget in
                volutpat mollis at volutpat lectus velit, sed auctor. Porttitor
                fames arcu quis fusce augue enim. Quis at habitant diam at.
                Suscipit tristique risus, at donec. In turpis vel et quam
                imperdiet. Ipsum molestie aliquet sodales id est ac volutpat.
              </p>
              <h3>Other resources</h3>
              <p>
                Sagittis et eu at elementum, quis in. Proin praesent volutpat
                egestas sociis sit lorem nunc nunc sit. Eget diam curabitur mi
                ac. Auctor rutrum lacus malesuada massa ornare et. Vulputate
                consectetur ac ultrices at diam dui eget fringilla tincidunt.
                Arcu sit dignissim massa erat cursus vulputate gravida id. Sed
                quis auctor vulputate hac elementum gravida cursus dis.
              </p>
              <ol>
                <li>Lectus id duis vitae porttitor enim gravida morbi.</li>
                <li>
                  Eu turpis posuere semper feugiat volutpat elit, ultrices
                  suspendisse. Auctor vel in vitae placerat.
                </li>
                <li>
                  Suspendisse maecenas ac donec scelerisque diam sed est duis
                  purus.
                </li>
              </ol>
              <figure>
                <img
                  className="h-60 md:h-96"
                  src="https://www.untitledui.com/marketing/girl-4.webp"
                  alt="Girl with a camera"
                />
                <figcaption>
                  <Link01 className="size-4 text-utility-gray-400" />
                  <span>
                    Image courtesy of Moose Photos via{" "}
                    <a
                      href="https://www.pexels.com/photo/colleagues-looking-at-laptop-1036641/"
                      className="rounded-xs outline-focus-ring focus-visible:outline-2 focus-visible:outline-offset-2"
                    >
                      Pexels
                    </a>
                  </span>
                </figcaption>
              </figure>
              <p>
                Lectus leo massa amet posuere. Malesuada mattis non convallis
                quisque. Libero sit et imperdiet bibendum quisque dictum
                vestibulum in non. Pretium ultricies tempor non est diam. Enim
                ut enim amet amet integer cursus. Sit ac commodo pretium sed
                etiam turpis suspendisse at.
              </p>
              <p>
                Tristique odio senectus nam posuere ornare leo metus, ultricies.
                Blandit duis ultricies vulputate morbi feugiat cras placerat
                elit. Aliquam tellus lorem sed ac. Montes, sed mattis
                pellentesque suscipit accumsan. Cursus viverra aenean magna
                risus elementum faucibus molestie pellentesque. Arcu ultricies
                sed mauris vestibulum.
              </p>
              <div className="not-prose my-8 rounded-2xl bg-secondary px-5 py-6 text-lg text-tertiary md:my-12 md:p-8 [&>p+p]:mt-4.5">
                <h2 className="mb-4 text-display-xs font-semibold text-primary">
                  Conclusion
                </h2>
                <p>
                  Morbi sed imperdiet in ipsum, adipiscing elit dui lectus.
                  Tellus id scelerisque est ultricies ultricies. Duis est sit
                  sed leo nisl, blandit elit sagittis. Quisque tristique
                  consequat quam sed. Nisl at scelerisque amet nulla purus
                  habitasse.
                </p>
                <p>
                  Nunc sed faucibus bibendum feugiat sed interdum. Ipsum egestas
                  condimentum mi massa. In tincidunt pharetra consectetur sed
                  duis facilisis metus. Etiam egestas in nec sed et. Quis
                  lobortis at sit dictum eget nibh tortor commodo cursus.
                </p>
                <p>
                  Odio felis sagittis, morbi feugiat tortor vitae feugiat fusce
                  aliquet. Nam elementum urna nisi aliquet erat dolor enim.
                  Ornare id morbi eget ipsum. Aliquam senectus neque ut id eget
                  consectetur dictum. Donec posuere pharetra odio consequat
                  scelerisque et, nunc tortor.
                </p>
              </div>
            </div>

            <div className="-mt-px border-t border-secondary pt-6">
              <div className="flex gap-2">
                <Badge color="blue-light" size="md">
                  Product
                </Badge>
                <Badge color="pink" size="md">
                  Tools
                </Badge>
                <Badge color="pink" size="md">
                  SaaS
                </Badge>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
