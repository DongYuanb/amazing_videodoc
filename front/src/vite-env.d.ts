/// <reference types="vite/client" />

// 解决 JSX runtime 类型问题
declare module 'react/jsx-runtime' {
  export * from 'react/jsx-runtime';
}

declare module 'react/jsx-dev-runtime' {
  export * from 'react/jsx-dev-runtime';
}
