/**
 * Local offline India states vector geometry data (no external CDN required).
 * State boundary paths mapped in standard 600x650 viewport coordinate space.
 */

export interface IndiaStatePath {
  code: string;
  name: string;
  path: string;
  centroid: [number, number];
}

export const INDIA_STATES_PATHS: IndiaStatePath[] = [
  {
    code: "JK",
    name: "Jammu & Kashmir",
    path: "M 205,30 L 255,25 L 290,55 L 295,95 L 250,115 L 210,105 L 185,80 Z",
    centroid: [240, 65],
  },
  {
    code: "HP",
    name: "Himachal Pradesh",
    path: "M 215,105 L 255,115 L 275,140 L 250,165 L 215,145 L 205,120 Z",
    centroid: [238, 132],
  },
  {
    code: "PB",
    name: "Punjab",
    path: "M 170,120 L 210,115 L 210,150 L 195,175 L 165,160 Z",
    centroid: [188, 142],
  },
  {
    code: "UT",
    name: "Uttarakhand",
    path: "M 250,140 L 295,150 L 305,185 L 275,195 L 245,170 Z",
    centroid: [275, 168],
  },
  {
    code: "HR",
    name: "Haryana",
    path: "M 195,165 L 235,160 L 235,190 L 205,210 L 185,185 Z",
    centroid: [210, 185],
  },
  {
    code: "DL",
    name: "Delhi",
    path: "M 225,182 L 237,180 L 240,192 L 227,194 Z",
    centroid: [232, 187],
  },
  {
    code: "RJ",
    name: "Rajasthan",
    path: "M 120,180 L 190,170 L 215,220 L 235,260 L 180,310 L 115,270 L 95,215 Z",
    centroid: [160, 235],
  },
  {
    code: "UP",
    name: "Uttar Pradesh",
    path: "M 235,185 L 300,190 L 385,245 L 365,290 L 285,290 L 250,250 L 235,220 Z",
    centroid: [305, 245],
  },
  {
    code: "BR",
    name: "Bihar",
    path: "M 385,245 L 455,245 L 450,290 L 380,295 L 365,275 Z",
    centroid: [415, 270],
  },
  {
    code: "GJ",
    name: "Gujarat",
    path: "M 65,280 L 130,270 L 165,320 L 135,380 L 90,375 L 50,335 Z",
    centroid: [105, 325],
  },
  {
    code: "MP",
    name: "Madhya Pradesh",
    path: "M 175,310 L 275,285 L 345,305 L 340,370 L 265,385 L 185,370 Z",
    centroid: [255, 340],
  },
  {
    code: "JH",
    name: "Jharkhand",
    path: "M 380,295 L 440,290 L 440,345 L 390,355 L 375,320 Z",
    centroid: [410, 320],
  },
  {
    code: "WB",
    name: "West Bengal",
    path: "M 445,260 L 470,255 L 470,360 L 435,380 L 435,330 L 455,290 Z",
    centroid: [455, 315],
  },
  {
    code: "OD",
    name: "Odisha",
    path: "M 360,360 L 425,350 L 440,410 L 375,445 L 350,405 Z",
    centroid: [395, 395],
  },
  {
    code: "MH",
    name: "Maharashtra",
    path: "M 130,375 L 225,370 L 290,370 L 305,420 L 235,465 L 155,455 L 140,410 Z",
    centroid: [215, 415],
  },
  {
    code: "TG",
    name: "Telangana",
    path: "M 240,425 L 295,415 L 305,465 L 255,485 L 235,455 Z",
    centroid: [270, 450],
  },
  {
    code: "AP",
    name: "Andhra Pradesh",
    path: "M 270,475 L 340,430 L 355,480 L 275,545 L 245,515 Z",
    centroid: [305, 495],
  },
  {
    code: "KA",
    name: "Karnataka",
    path: "M 175,455 L 235,465 L 245,540 L 210,580 L 175,525 Z",
    centroid: [205, 510],
  },
  {
    code: "GA",
    name: "Goa",
    path: "M 165,490 L 178,490 L 176,505 L 163,502 Z",
    centroid: [170, 498],
  },
  {
    code: "KL",
    name: "Kerala",
    path: "M 185,550 L 210,555 L 215,615 L 195,620 Z",
    centroid: [198, 585],
  },
  {
    code: "TN",
    name: "Tamil Nadu",
    path: "M 215,540 L 265,540 L 255,615 L 210,615 L 220,570 Z",
    centroid: [240, 575],
  },
  {
    code: "AS",
    name: "Assam",
    path: "M 480,230 L 545,215 L 565,245 L 515,265 L 485,255 Z",
    centroid: [520, 240],
  },
  {
    code: "NE",
    name: "North East Region",
    path: "M 525,190 L 575,200 L 585,270 L 535,275 Z",
    centroid: [555, 230],
  },
];
