import js from "@eslint/js";
import { defineConfig } from "eslint/config";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

// Propiedades y métodos con los que el DOM interpreta una cadena como HTML
const htmlSinks = "^(innerHTML|outerHTML|insertAdjacentHTML|setHTML)$";
const documentWriters = "^write(ln)?$";
const ofDocument = ":matches([object.name='document'], [object.property.name='document'])";

// Todo texto de usuario entra como texto de React, nunca como HTML
const forbiddenSyntax = [
  "JSXAttribute[name.name='dangerouslySetInnerHTML']",
  "Property[key.name='dangerouslySetInnerHTML']",
  "Property[key.value='dangerouslySetInnerHTML']",
  `MemberExpression[computed=false][property.name=/${htmlSinks}/]`,
  `MemberExpression[computed=true][property.value=/${htmlSinks}/]`,
  `MemberExpression[computed=true][property.quasis.0.value.cooked=/${htmlSinks}/]`,
  `MemberExpression${ofDocument}[computed=false][property.name=/${documentWriters}/]`,
  `MemberExpression${ofDocument}[computed=true][property.value=/${documentWriters}/]`,
];

export default defineConfig(
  { ignores: ["dist", "src/api/schema.gen.ts"] },
  js.configs.recommended,
  tseslint.configs.recommended,
  reactHooks.configs.flat.recommended,
  {
    languageOptions: { globals: globals.browser },
    rules: {
      "no-restricted-syntax": [
        "error",
        ...forbiddenSyntax.map((selector) => ({ selector, message: "No se inyecta HTML." })),
      ],
    },
  },
);
