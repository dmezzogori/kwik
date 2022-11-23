import kwik


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 0:
        from kwik.api.api import api_router

        k = kwik.Kwik(api_router)
        kwik.run(k)
    else:
        kwik.run(sys.argv[1])
