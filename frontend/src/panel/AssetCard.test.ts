import { isValidElement, type ImgHTMLAttributes, type ReactElement, type ReactNode, type SyntheticEvent } from "react";
import { describe, expect, it } from "vitest";

import type { components } from "../api/schema.gen";
import { AssetCard } from "./AssetCard";

type PublicAsset = components["schemas"]["PublicAsset"];
type ImageProps = ImgHTMLAttributes<HTMLImageElement>;
type FakeImage = { src: string; style: { visibility: string } };

const ASSET: PublicAsset = {
  public_id: "3f0c1f2e-5b7a-4c1d-9e8f-0a1b2c3d4e01",
  title: "Bien 1",
  category_slug: "kayak",
  category_name: "Kayak",
  price: "12.50",
  currency: "EUR",
  price_unit: "day",
  privacy_radius: 500,
  latitude: 39.45,
  longitude: -0.37,
};

function childrenOf(node: ReactNode): ReactNode[] {
  if (!isValidElement<{ children?: ReactNode }>(node)) return [];
  return [node.props.children].flat();
}

function imageElements(node: ReactNode): ReactElement<ImageProps>[] {
  if (!isValidElement<ImageProps>(node)) return [];
  const own = node.type === "img" ? [node] : [];
  return [...own, ...childrenOf(node).flatMap(imageElements)];
}

function cardImage(): ReactElement<ImageProps> {
  const images = imageElements(AssetCard({ asset: ASSET }));
  expect(images).toHaveLength(1);
  return images[0]!;
}

// Sin DOM en los tests: el evento solo necesita la imagen como currentTarget
const eventOn = (image: FakeImage) => ({ currentTarget: image }) as unknown as SyntheticEvent<HTMLImageElement>;

// renderToStaticMarkup no pinta los manejadores: se llama al componente y se disparan sobre una imagen falsa
describe("AssetCard: imagen que no llega", () => {
  it("si la imagen falla, se oculta y conserva su hueco de 72 px", () => {
    const image = cardImage();
    const fake: FakeImage = { src: String(image.props.src), style: { visibility: "" } };

    expect(image.props.onError).toBeTypeOf("function");
    image.props.onError?.(eventOn(fake));

    expect(fake.style.visibility).toBe("hidden");
    expect(image.props.width).toBe(72);
    expect(image.props.height).toBe(72);
  });

  it("si después cambia el src y la imagen carga, vuelve a verse", () => {
    const image = cardImage();
    const fake: FakeImage = { src: String(image.props.src), style: { visibility: "" } };

    expect(image.props.onError).toBeTypeOf("function");
    expect(image.props.onLoad).toBeTypeOf("function");
    image.props.onError?.(eventOn(fake));
    fake.src = "/src/assets/categories/other.webp?no-inline";
    image.props.onLoad?.(eventOn(fake));

    expect(fake.style.visibility).toBe("visible");
  });
});
