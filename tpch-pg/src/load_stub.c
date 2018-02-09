/*
 * $Id: load_stub.c,v 1.2 2005/01/03 20:08:58 jms Exp $
 *
 * Revision History
 * ===================
 * $Log: load_stub.c,v $
 * Revision 1.2  2005/01/03 20:08:58  jms
 * change line terminations
 *
 * Revision 1.1.1.1  2004/11/24 23:31:46  jms
 * re-establish external server
 *
 * Revision 1.1.1.1  2003/04/03 18:54:21  jms
 * recreation after CVS crash
 *
 * Revision 1.1.1.1  2003/04/03 18:54:21  jms
 * initial checkin
 *
 *
 */
/*****************************************************************
 *  Title:      load_stub.c
 *  Description:
 *              stub routines for:
 *          inline load of dss benchmark
 *          header creation for dss benchmark
 *
 *****************************************************************
 */

#include <stdio.h>
#include "config.h"
#include "dss.h"
#include "dsstypes.h"

#include <libpq-fe.h>

int ld_drange PROTO((int tbl, DSS_HUGE min, DSS_HUGE cnt, long num));

static void
exit_nicely(PGconn *conn)
{
    PQfinish(conn);
    exit(-2);
}


PGconn *
open_pgconn_and_begin()
{
	PGconn     *conn;
	PGresult   *res;

	/* Make a connection to the database */
	conn = PQconnectdb(db_name);

	/* Check to see that the backend connection was successfully made */
	if (PQstatus(conn) != CONNECTION_OK)
	{
		fprintf(stderr, "Connection to database failed: %s",
				PQerrorMessage(conn));
		exit_nicely(conn);
	}

	/* Start a transaction block */
	res = PQexec(conn, "BEGIN");

	if (PQresultStatus(res) != PGRES_COMMAND_OK)
	{
		fprintf(stderr, "BEGIN command failed: %s", PQerrorMessage(conn));
		PQclear(res);
		exit_nicely(conn);
	}
	PQclear(res);

	return conn;
}


int
commit_and_close(PGconn *conn)
{
	PGresult   *res;

    /* end the transaction */
    res = PQexec(conn, "COMMIT");
	if (PQresultStatus(res) != PGRES_COMMAND_OK)
	{
		fprintf(stderr, "COMMIT command failed: %s", PQerrorMessage(conn));
		PQclear(res);
		exit_nicely(conn);
	}
    PQclear(res);

    /* close the connection to the database and cleanup */
    PQfinish(conn);

    return(0);
}


PGconn *
prep_direct(const char *tablename)
{
	PGconn     *conn = open_pgconn_and_begin();
	PGresult   *res;
	PQExpBuffer q = createPQExpBuffer();

	/* Open the COPY stream */
	printfPQExpBuffer(q, "COPY %s FROM STDIN;", tablename);

    res = PQexec(conn, q->data);

    if (PQresultStatus(res) != PGRES_COPY_IN)
    {
        fprintf(stderr, "COPY command failed: %s", PQerrorMessage(conn));
        PQclear(res);
        exit_nicely(conn);
    }
    PQclear(res);

    return conn;
}


int
close_direct(PGconn *conn)
{
	PGresult   *res;
	int status;

	/* end the current COPY stream */
	status = PQputCopyEnd(conn, NULL);

    if (status != 1)
    {
        fprintf(stderr, "COPY command failed: %s", PQerrorMessage(conn));
        exit_nicely(conn);
    }

	/*
	 * After successfully calling PQputCopyEnd, call PQgetResult to obtain the
	 * final result status of the COPY command. One can wait for this result to
	 * be available in the usual way. Then return to normal operation.
	 */
	res = PQgetResult(conn);
	if (PQresultStatus(res) != PGRES_COMMAND_OK)
	{
		fprintf(stderr, "COMMIT command failed: %s", PQerrorMessage(conn));
		PQclear(res);
		exit_nicely(conn);
	}
    PQclear(res);

    /* end the transaction and close the connection */
	commit_and_close(conn);

    return(0);
}



void
copyrow(PGconn *conn, const char *data, int len)
{
	int status = PQputCopyData(conn, data, len);

	if (status == -1)
	{
        fprintf(stderr, "COPY command failed: %s", PQerrorMessage(conn));
        exit_nicely(conn);
	}
	else if (status == 0)
	{
        fprintf(stderr, "COPY command failed: full buffers!");
        exit_nicely(conn);
	}
	return;
}

int
pg_append(int format, PQExpBuffer buffer, void *data, int len, int sep)
{
	int dollars,
		cents;

	switch(format)
	{
		case DT_STR:
			appendPQExpBuffer(buffer, "%s", (char *)data);
			break;
#ifdef MVS
		case DT_VSTR:
			/* note: only used in MVS, assumes columnar output */
			appendPQExpBuffer(buffer, "%c%c%-*s",
					(len >> 8) & 0xFF, len & 0xFF, len, (char *)data);
			break;
#endif /* MVS */
		case DT_INT:
			appendPQExpBuffer(buffer, "%ld", (long)data);
			break;
		case DT_HUGE:
			appendPQExpBuffer(buffer, HUGE_FORMAT, *(DSS_HUGE *)data);
			break;
		case DT_KEY:
			appendPQExpBuffer(buffer, "%ld", (long)data);
			break;
		case DT_MONEY:
			cents = (int)*(DSS_HUGE *)data;
			if (cents < 0)
			{
				appendPQExpBuffer(buffer, "-");
				cents = -cents;
			}
			dollars = cents / 100;
			cents %= 100;
			appendPQExpBuffer(buffer, "%d.%02d", dollars, cents);
			break;
		case DT_CHR:
			appendPQExpBuffer(buffer, "%c", *(char *)data);
			break;

		case DT_EOL:
			appendPQExpBuffer(buffer, "\n");
	}

	if (sep)
		/* COPY Separator is a TAB character */
		appendPQExpBuffer(buffer, "\t");

	return(0);
}

int
ld_cust (customer_t *c, int mode, DSS_HUGE start, DSS_HUGE count, DSS_HUGE rownum)
{
	static PGconn *conn = NULL;
	PQExpBuffer fp;

	if (rownum == start)
	{
		conn = prep_direct("CUSTOMER");
	}

	LD_STRT(fp);
	LD_HUGE(fp, &c->custkey);
	if (scale <= 3000)
		LD_VSTR(fp, c->name, C_NAME_LEN);
	else
		LD_VSTR(fp, c->name, C_NAME_LEN + 3);
	LD_VSTR(fp, c->address, c->alen);
	LD_HUGE(fp, &c->nation_code);
	LD_STR(fp, c->phone, PHONE_LEN);
	LD_MONEY(fp, &c->acctbal);
	LD_STR(fp, c->mktsegment, C_MSEG_LEN);
	LD_VSTR_LAST(fp, c->comment, c->clen);
	LD_END(fp);

	copyrow(conn, fp->data, fp->len);

	if (count == 1)
	{
		close_direct(conn);
	}

    return(0);
}


int
ld_order (order_t *o, int mode, DSS_HUGE start, DSS_HUGE count, DSS_HUGE rownum)
{
	static PGconn *conn = NULL;
	PQExpBuffer fp_o;

	if (rownum == start)
	{
		conn = prep_direct("ORDERS");
	}

    LD_STRT(fp_o);
    LD_HUGE(fp_o, &o->okey);
    LD_HUGE(fp_o, &o->custkey);
    LD_CHR(fp_o, &o->orderstatus);
    LD_MONEY(fp_o, &o->totalprice);
    LD_STR(fp_o, o->odate, DATE_LEN);
    LD_STR(fp_o, o->opriority, O_OPRIO_LEN);
    LD_STR(fp_o, o->clerk, O_CLRK_LEN);
    LD_INT(fp_o, o->spriority);
    LD_VSTR_LAST(fp_o, o->comment, o->clen);
    LD_END(fp_o);

	copyrow(conn, fp_o->data, fp_o->len);

	if (count == 1)
	{
		close_direct(conn);
	}
    return(0);
}


int ld_line (order_t *o, int mode, DSS_HUGE start, DSS_HUGE count, DSS_HUGE rownum)
{
	static PGconn *conn = NULL;
	PQExpBuffer fp_l;
    long      i;

	if (rownum == start)
	{
		conn = prep_direct("LINEITEM");
	}

    for (i = 0; i < o->lines; i++)
	{
        LD_STRT(fp_l);
        LD_HUGE(fp_l, &o->l[i].okey);
        LD_HUGE(fp_l, &o->l[i].partkey);
        LD_HUGE(fp_l, &o->l[i].suppkey);
        LD_HUGE(fp_l, &o->l[i].lcnt);
        LD_HUGE(fp_l, &o->l[i].quantity);
        LD_MONEY(fp_l, &o->l[i].eprice);
        LD_MONEY(fp_l, &o->l[i].discount);
        LD_MONEY(fp_l, &o->l[i].tax);
        LD_CHR(fp_l, &o->l[i].rflag[0]);
        LD_CHR(fp_l, &o->l[i].lstatus[0]);
        LD_STR(fp_l, o->l[i].sdate, DATE_LEN);
        LD_STR(fp_l, o->l[i].cdate, DATE_LEN);
        LD_STR(fp_l, o->l[i].rdate, DATE_LEN);
        LD_STR(fp_l, o->l[i].shipinstruct, L_INST_LEN);
        LD_STR(fp_l, o->l[i].shipmode, L_SMODE_LEN);
        LD_VSTR_LAST(fp_l, o->l[i].comment,o->l[i].clen);
        LD_END(fp_l);

		copyrow(conn, fp_l->data, fp_l->len);
	}

	if (count == 1)
	{
		close_direct(conn);
	}

    return(0);
}


int
ld_order_line (order_t *p, int mode, DSS_HUGE start, DSS_HUGE count, DSS_HUGE rownum)
{
    tdefs[ORDER].name = tdefs[ORDER_LINE].name;
    ld_order(p, mode, start, count, rownum);
    ld_line (p, mode, start, count, rownum);

    return(0);
}


int
ld_part (part_t *part, int mode, DSS_HUGE start, DSS_HUGE count, DSS_HUGE rownum)
{
	static PGconn *conn = NULL;
	PQExpBuffer p_fp;

	if (rownum == start)
	{
		conn = prep_direct("PART");
	}

	LD_STRT(p_fp);
	LD_HUGE(p_fp, &part->partkey);
	LD_VSTR(p_fp, part->name,part->nlen);
	LD_STR(p_fp, part->mfgr, P_MFG_LEN);
	LD_STR(p_fp, part->brand, P_BRND_LEN);
	LD_VSTR(p_fp, part->type,part->tlen);
	LD_HUGE(p_fp, &part->size);
	LD_STR(p_fp, part->container, P_CNTR_LEN);
	LD_MONEY(p_fp, &part->retailprice);
	LD_VSTR_LAST(p_fp, part->comment,part->clen);
	LD_END(p_fp);

	copyrow(conn, p_fp->data, p_fp->len);

	if (count == 1)
	{
		close_direct(conn);
	}

    return(0);
}

int
ld_psupp (part_t *part, int mode, DSS_HUGE start, DSS_HUGE count, DSS_HUGE rownum)
{
	static PGconn *conn = NULL;
	PQExpBuffer ps_fp;
    long      i;

	if (rownum == start)
	{
		conn = prep_direct("PARTSUPP");
	}

	for (i = 0; i < SUPP_PER_PART; i++)
	{
		LD_STRT(ps_fp);
		LD_HUGE(ps_fp, &part->s[i].partkey);
		LD_HUGE(ps_fp, &part->s[i].suppkey);
		LD_HUGE(ps_fp, &part->s[i].qty);
		LD_MONEY(ps_fp, &part->s[i].scost);
		LD_VSTR_LAST(ps_fp, part->s[i].comment,part->s[i].clen);
		LD_END(ps_fp);

		copyrow(conn, ps_fp->data, ps_fp->len);
	}

	if (count == 1)
	{
		close_direct(conn);
	}

    return(0);
}


int
ld_part_psupp (part_t *p, int mode, DSS_HUGE start, DSS_HUGE count, DSS_HUGE rownum)
{
    tdefs[PART].name = tdefs[PART_PSUPP].name;
    ld_part(p, mode, start, count, rownum);
    ld_psupp (p, mode, start, count, rownum);

    return(0);
}


int
ld_supp (supplier_t *supp, int mode, DSS_HUGE start, DSS_HUGE count, DSS_HUGE rownum)
{
	static PGconn *conn = NULL;
	PQExpBuffer fp;

	if (rownum == start)
	{
		conn = prep_direct("SUPPLIER");
	}

	LD_STRT(fp);
	LD_HUGE(fp, &supp->suppkey);
	LD_STR(fp, supp->name, S_NAME_LEN);
	LD_VSTR(fp, supp->address, supp->alen);
	LD_HUGE(fp, &supp->nation_code);
	LD_STR(fp, supp->phone, PHONE_LEN);
	LD_MONEY(fp, &supp->acctbal);
	LD_VSTR_LAST(fp, supp->comment, supp->clen);
	LD_END(fp);

	copyrow(conn, fp->data, fp->len);

	if (count == 1)
	{
		close_direct(conn);
	}

    return(0);
}


int
ld_nation (code_t *c, int mode, DSS_HUGE start, DSS_HUGE count, DSS_HUGE rownum)
{
	static PGconn *conn = NULL;
	PQExpBuffer fp;

	if (rownum == start)
	{
		conn = prep_direct("NATION");
	}

	LD_STRT(fp);
	LD_HUGE(fp, &c->code);
	LD_STR(fp, c->text, NATION_LEN);
	LD_INT(fp, c->join);
	LD_VSTR_LAST(fp, c->comment, c->clen);
	LD_END(fp);

	copyrow(conn, fp->data, fp->len);

	if (count == 1)
	{
		close_direct(conn);
	}

    return(0);
}


int
ld_region (code_t *c, int mode, DSS_HUGE start, DSS_HUGE count, DSS_HUGE rownum)
{
	static PGconn *conn = NULL;
	PQExpBuffer fp;

	if (rownum == start)
	{
		conn = prep_direct("REGION");
	}

	LD_STRT(fp);
	LD_HUGE(fp, &c->code);
	LD_STR(fp, c->text, REGION_LEN);
	LD_VSTR_LAST(fp, c->comment, c->clen);
	LD_END(fp);

	copyrow(conn, fp->data, fp->len);

	if (count == 1)
	{
		close_direct(conn);
	}

    return(0);
}


/*
 * This function isn't part of the tdefs meta-data.
 *
 * We implement here "Old Sales Refresh Function (RF2)" and directly issue the
 * DELETE statements to the database connection.
 */
int
ld_drange(int tbl, DSS_HUGE min, DSS_HUGE cnt, long num)
{
    static int  last_num = 0;
    static PGconn *conn = NULL;
    DSS_HUGE child = -1;
    DSS_HUGE start, last, new;

	static DSS_HUGE rows_per_segment=0;
	static DSS_HUGE rows_this_segment=0;

    if (last_num != num)
	{
        if (conn)
		{
            commit_and_close(conn);
		}
		conn = open_pgconn_and_begin();

        last_num = num;
		rows_this_segment=0;
	}

    start = MK_SPARSE(min, num/ (10000 / UPD_PCT));
    last = start - 1;
    for (child=min; cnt > 0; child++, cnt--)
	{
		PGresult   *res;
		PQExpBuffer q = createPQExpBuffer();

		new = MK_SPARSE(child, num/ (10000 / UPD_PCT));
		if (delete_segments)
		{

			if(rows_per_segment==0)
				rows_per_segment = (cnt / delete_segments) + 1;
			if((++rows_this_segment) > rows_per_segment)
			{
				commit_and_close(conn);
				conn = open_pgconn_and_begin();

				last_num = num;
				rows_this_segment=1;
			}
		}

		/* now issue the DELETE statements */
		printfPQExpBuffer(q, "DELETE FROM LINEITEM WHERE L_ORDERKEY = %lld;", new);

		res = PQexec(conn, q->data);
		if (PQresultStatus(res) != PGRES_COMMAND_OK)
		{
			fprintf(stderr, "DELETE failed: %s", PQerrorMessage(conn));
			PQclear(res);
			exit_nicely(conn);
		}
		PQclear(res);

		printfPQExpBuffer(q, "DELETE FROM ORDERS WHERE O_ORDERKEY = %lld;", new);

		res = PQexec(conn, q->data);
		if (PQresultStatus(res) != PGRES_COMMAND_OK)
		{
			fprintf(stderr, "DELETE failed: %s", PQerrorMessage(conn));
			PQclear(res);
			exit_nicely(conn);
		}
		PQclear(res);

		start = new;
		last = new;
	}

    return(0);
}
